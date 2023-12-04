import logging
from ryu.base import app_manager

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_2
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib import hub
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host
from ryu import cfg
from ryu.app import simple_switch_13
from collections import defaultdict
import networkx
from main.controller.netstate.netstate_config import *

CONF = cfg.CONF

events = [event.EventSwitchEnter, event.EventSwitchLeave, event.EventPortAdd,
          event.EventPortDelete, event.EventPortModify, event.EventLinkAdd,
          event.EventLinkDelete, event.EventHostAdd, event.EventHostDelete]


class Topology(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        """
        link_to_port:
            记录某条链路两端的设备信息，当两端都是交换机，则格式为：(dpid, port):(dpid,port)
            当一段为主机，则格式为：(dpid, port):(mac, ip)
        host_or_switch: 
            交换机某个端口连接的是交换机（1）还是客户端（2），形式为：(dpid, port):1/2
        switch_port_table:
            交换机有哪些port，格式为dpid:[1,2,3] 
        switch_ip_address:
            dpid:ip_address 交换机连接控制器的ip地址
        """
        super(Topology, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.link_to_port = {}
        self.host_or_switch = {}
        self.switch_port_table = {}
        self.switch_ip_address = {}

        # dpid1:{ dpid2:(port1, port2), dpid3:(port1, port2) }, 两个交换机之间通过各自的哪个port连接在一起
        # port1, port2 = port_topo[1][2], 说明1号交换机的port1口和2号交换机的port2口相连
        self.port_topo = defaultdict(dict)
        self.datapaths = {}
        self.graph = networkx.graph.Graph()  # 网络拓扑结构
        self.name = app_topology_name
        self.discover_thread = hub.spawn(self._discover_links)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handle(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.switch_ip_address[datapath.id] = datapath.address
        self.datapaths[datapath.id] = datapath
        self.logger.info("switch %s is connected, ip: %s", datapath.id, datapath.address)

        # 下发默认流表（packet in）
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath=datapath, priority=0, actions=actions, match=match)

    def add_flow(self, datapath, priority, actions, match, idle_timeout=0, hard_timeout=0):
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout, match=match, instructions=inst)

        datapath.send_msg(mod)

    # A thread to output the information of topology
    def _discover_links(self):
        while True:
            self.get_topology(None)
            self.logger.info(self.link_to_port)
            # self.logger.info(self.host_or_switch)
            hub.sleep(5)

    # fill the port of switch imformation
    def create_map(self, switch_list):
        for sw in switch_list:
            dpid = sw.dp.id
            self.switch_port_table.setdefault(dpid, set())

            for p in sw.ports:
                self.switch_port_table[dpid].add(p.port_no)
            # add graph node
            self.graph.add_node(dpid)

    # fill the link information
    def create_link_port(self, link_list, host_list):
        for link in link_list:
            src = link.src
            dst = link.dst
            self.link_to_port[(src.dpid, src.port_no)] = (dst.dpid, dst.port_no)
            self.link_to_port[(dst.dpid, dst.port_no)] = (src.dpid, src.port_no)
            self.host_or_switch[(src.dpid, src.port_no)] = 1
            self.host_or_switch[(dst.dpid, dst.port_no)] = 1
            self.port_topo[src.dpid][dst.dpid] = (src.port_no, dst.port_no)
            self.port_topo[dst.dpid][src.dpid] = (dst.port_no, src.port_no)
            # add edge between nodes
            self.graph.add_edge(src.dpid, dst.dpid)
        # self.logger.info(host_list)
        for host in host_list:
            port = host.port
            self.link_to_port[(port.dpid, port.port_no)] = (host.mac, host.ipv4)
            self.host_or_switch[(port.dpid, port.port_no)] = 2

    # monitor the change in link information

    @set_ev_cls(events)
    def get_topology(self, ev):
        # self.logger.info("get topology")
        switch_list = get_switch(self.topology_api_app)
        self.create_map(switch_list=switch_list)
        self.create_link_port(get_link(self.topology_api_app), get_host(self.topology_api_app))
