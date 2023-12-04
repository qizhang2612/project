from operator import attrgetter
from collections import defaultdict
from ryu.base import app_manager
from ryu.lib import hub
from ryu.app import simple_switch_13
from ryu.ofproto import ofproto_v1_3, ether
from ryu.lib.packet import ethernet, packet, ipv4, udp
from ryu.ofproto.inet import *
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from flow_mod import FlowMod
from netstate_config import *
from ofp_ants_message import *
import time
import copy


class PortState:
    def __init__(self) -> None:
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.capacity = 0
        self.used_bw = 0
        self.sec = 0
        self.nsec = 0

    def print_state_info(self):
        print("tx\trx\tcapacity\tused_bw\n{}\t{}\t{}\t{}".format(
            self.tx_bytes, self.rx_bytes, self.capacity, self.used_bw))


class LinkState(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs) -> None:
        super(LinkState, self).__init__(*_args, **_kwargs)
        """
        link_state:
            存储着链路上的信息，key为dpid，value为一个字典，dp_id:{port_id:PortState}。该字典记录
            每个该交换机网口所连接的链路的信息。
        """
        self.link_state = defaultdict(dict)
        self.datapaths = {}
        self.name = app_link_state_name
        self.flow_mod = FlowMod()
        self.monitor_thread = hub.spawn(self._monitor_link_state)

    # request port rx/tx info
    def _request_port_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    # request link capacity
    def _request_port_desc_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortDescStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    def _show_state(self):
        for dct in self.link_state:
            print("dp_id {}".format(dct))
            for port in self.link_state[dct]:
                print("port {}".format(port))
                self.link_state[dct][port].print_state_info()

    def _monitor_link_state(self):
        hub.sleep(10)
        while True:
            for datapath in self.datapaths.values():
                self._request_port_desc_stats(datapath=datapath)
                hub.sleep(1)
                self._request_port_stats(datapath=datapath)
            hub.sleep(LINK_STATE_PROBE_INTERVAL-1)
            self._show_state()

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath in self.datapaths:
                self.logger.info("register datapath: %016x", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath in self.datapaths:
                self.logger.info("unregister datapath %016x", datapath.id)
                self.datapaths.pop(datapath.id)
                self.link_state.pop(datapath.id)

    def _update_link_state(self, dp_id, rx_bytes, tx_bytes, port, sec, nsec):
        # 过滤掉交换机与控制器之间的port信息，该port通常是一串很大的整形数字，因此通过
        # 下面方式做简单过滤
        if port > MAX_PORT_NUM:
            return
        if self.link_state.get(dp_id) and self.link_state[dp_id].get(port):
            pre_state = self.link_state[dp_id][port]
        else:
            self.link_state[dp_id][port] = PortState()
            pre_state = self.link_state[dp_id][port]
        period = sec + nsec/10**9 - pre_state.sec - pre_state.nsec/10**9
        speed = (tx_bytes + rx_bytes - pre_state.tx_bytes - pre_state.rx_bytes) * 8 / period
        speed = int(speed / 1000000)  # Mbps
        pre_state.rx_bytes = rx_bytes
        pre_state.tx_bytes = tx_bytes
        pre_state.used_bw = speed
        pre_state.sec = sec
        pre_state.nsec = nsec

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        body = ev.msg.body
        for stat in sorted(body, key=attrgetter('port_no')):
            self._update_link_state(dp_id=ev.msg.datapath.id, rx_bytes=stat.rx_bytes, tx_bytes=stat.tx_bytes,
                                    port=stat.port_no, nsec=stat.duration_nsec, sec=stat.duration_sec)

    def _update_link_capacity(self, dp_id, port, link_capacity):
        if port > MAX_PORT_NUM:
            return
        if self.link_state.get(dp_id) and self.link_state[dp_id].get(port):
            pre_state = self.link_state[dp_id][port]
        else:
            self.link_state[dp_id][port] = PortState()
            pre_state = self.link_state[dp_id][port]
        pre_state.capacity = int(link_capacity / 1000)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        dp_id = ev.msg.datapath.id
        body = ev.msg.body
        for p in body:
            self._update_link_capacity(dp_id=dp_id, port=p.port_no, link_capacity=p.curr_speed)
