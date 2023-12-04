from operator import attrgetter
from collections import defaultdict
from ryu.base import app_manager
from ryu.lib import hub
from ryu.app import simple_switch_13
from ryu.ofproto import ofproto_v1_3, ether, ofproto_v1_0, ofproto_v1_2
from ryu.lib.packet import ethernet, packet, ipv4, udp
from ryu.ofproto.inet import *
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from flow_mod import FlowMod
from netstate_config import *
import time
import networkx
import copy


class LinkDelay(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        """
        delay:
            存储着时延探测的最新数据，直接从该变量获取时延，获取方式为 t = self.delay[dpid1][dpid2]
        """
        super().__init__(*_args, **_kwargs)
        self.probe_switch_lists = []
        self.probe_port_lists = []
        self.delay = defaultdict(dict)
        self.name = app_link_delay_name
        self.flow_mod = FlowMod()
        self.probe_thread = hub.spawn(self.auto_probe)

        # 依赖topology生成的网络拓扑
        self.app_topology = app_manager.lookup_service_brick(app_topology_name)
        # 依赖link state维护的交换机datapath信息，也可以自己收集
        self.app_link_state = app_manager.lookup_service_brick(app_link_state_name)

    def _construct_detect_packet(self):
        e = ethernet.ethernet(dst=LINK_DELAY_MAC_DST, src=LINK_DELAY_MAC_SRC, ethertype=ether.ETH_TYPE_IP)
        ip = ipv4.ipv4(src=LINK_DELAY_SRC, dst=LINK_DELAY_DST, proto=IPPROTO_UDP)
        udp_ = udp.udp(src_port=1000, dst_port=1001)
        payload = '\x00'*1440
        pkt = packet.Packet()
        pkt.add_protocol(e)
        pkt.add_protocol(ip)
        pkt.add_protocol(udp_)
        pkt.serialize()
        return pkt.data + bytearray(payload, 'utf-8')

    def probe_link_delay(self, switch_list, port_list):
        # send flow mod
        datapaths = self.app_link_state.datapaths
        if len(port_list) < 2:
            return
        for i in range(len(switch_list)):
            in_port, out_port = port_list[i]
            if datapaths.get(switch_list[i]):
                datapath = datapaths[switch_list[i]]
            else:
                self.logger.info("unknown dpid in probe link delay")
                return
            ofproto = datapath.ofproto
            if i == len(switch_list) - 1:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=LINK_DELAY_SRC, dst_ip=LINK_DELAY_DST,
                                               in_port=in_port, out_port=ofproto.OFPP_CONTROLLER)
            elif i == 0:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=LINK_DELAY_SRC, dst_ip=LINK_DELAY_DST,
                                               in_port=ofproto.OFPP_CONTROLLER, out_port=out_port)
            else:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=LINK_DELAY_SRC, dst_ip=LINK_DELAY_DST,
                                               in_port=in_port, out_port=out_port)                
        # 睡眠，保证在流表下发之后探测包才被下发到交换机中
        time.sleep(0.05)

        # send probe packet
        pkt = self._construct_detect_packet()
        datapath = datapaths[switch_list[0]]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=ofproto.OFPP_TABLE)]
        msg = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions, data=pkt)
        datapath.send_msg(msg)

    def _deep_search(self, graph, depth_limit=None) -> list:
        degree_map = dict(graph.degree())
        odd = False
        source = 1
        edges = graph.number_of_edges() + 1
        for node, degree in degree_map.items():
            if degree % 2 == 0:
                if not odd and degree < edges:
                    edges = degree
                    source = node
            else:
                if (odd and degree < edges) or (not odd):
                    edges = degree
                    source = node

        re = list()
        if depth_limit is None:
            depth_limit = len(degree_map)
        while len(re) < depth_limit:
            re.append(source)
            neighbors = list(graph.neighbors(source))
            if len(neighbors) == 0:
                graph.remove_node(source)
                break
            edges = -1
            for node in neighbors:
                if degree_map[node] > edges:
                    next_node = node
            graph.remove_edge(source, next_node)
            degree_map[source] -= 1
            degree_map[next_node] -= 1
            if degree_map[source] <= 0 and len(re) < depth_limit:
                graph.remove_node(source)
            source = next_node

        return re

    def _get_port_list(self, switch_list) -> list:
        re = []
        for i in range(len(switch_list)):
            dpid = switch_list[i]
            if i == 0:
                out_port = self.app_topology.port_topo[dpid][switch_list[i+1]][0]
                re.append((out_port, out_port))
                continue
            pre_dpid = switch_list[i-1]
            in_port = self.app_topology.port_topo[dpid][pre_dpid][0]
            if i == len(switch_list) - 1:
                re.append((in_port, in_port))
                continue
            next_dpid = switch_list[i+1]
            out_port = self.app_topology.port_topo[dpid][next_dpid][0]
            re.append((in_port, out_port))

        return re

    def _generate_probe_path(self, graph):
        while len(graph) != 0:
            # 计算一条探测路径
            switch_list = self._deep_search(graph=graph)
            # 少于两条交换机，不够组成一条路径，则不进行探测
            if len(switch_list) < 2:
                continue
            # 计算路径交换机的出入port
            print("switch list: ",switch_list)
            port_list = self._get_port_list(switch_list=switch_list)
            print("port list:", port_list)
            self.probe_switch_lists.append(switch_list)
            self.probe_port_lists.append(port_list)

    def auto_probe(self):
        # 30s 等待拓扑获取成功
        hub.sleep(30)
        self.logger.info("start auto probe link delay")
        while True:
            # 探测序列为0说明上一轮探测任务已经完成，可以开始下一轮
            # 否则等待直到上一轮完成
            if len(self.probe_switch_lists) != 0:
                hub.sleep(1)
                continue
            graph = copy.deepcopy(self.app_topology.graph)
            # 从graph中计算得到时延探测的交换机序列，可能有多次探测，所以有多个序列
            self._generate_probe_path(graph=graph)
            # 从第一个序列开始探测，当packet in收到上传的探测包后，删除该交换机序列
            # 然后在探测包处理函数中选取下一个序列进行探测
            # 必须收到上个探测包之后才进行下一次探测，避免流表冲突问题
            if len(self.probe_switch_lists) > 0:
                self.probe_link_delay(self.probe_switch_lists[0], self.probe_port_lists[0])
            hub.sleep(3)

    # called by packet in handler
    def probe_packet_handler(self, pkt_data):
        begin = ETH_LEN + IP_LEN + UDP_LEN
        payload = pkt_data[begin:len(pkt_data)]
        count = int.from_bytes(payload[0:1], byteorder='big')
        self.logger.info("count: %d", count)
        time_stamp_list = []
        offset = 1
        for i in range(count):
            time_stamp = int.from_bytes(payload[offset:offset+TS_LEN], byteorder='big')
            time_stamp_list.append(time_stamp)
            offset += TS_LEN
        print("ts:", time_stamp_list)
        switch_list = self.probe_switch_lists[0]
        for i in range(1, count):
            delay = time_stamp_list[i] - time_stamp_list[i-1]
            self.delay[switch_list[i]][switch_list[i-1]] = delay
            self.delay[switch_list[i-1]][switch_list[i]] = delay
            self.logger.info("%d %d delay:%d", switch_list[i], switch_list[i-1], delay)

        self.probe_port_lists.pop(0)
        self.probe_switch_lists.pop(0)
        if len(self.probe_switch_lists) > 0:
            self.probe_link_delay(self.probe_switch_lists[0], self.probe_port_lists[0])

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        ip_header = pkt.get_protocol(ipv4.ipv4)
        if ip_header:
            src_ip, dst_ip = ip_header.src, ip_header.dst
            if src_ip == LINK_DELAY_SRC and dst_ip == LINK_DELAY_DST:
                self.logger.info("recv link delay detect packet")
                # print(pkt.data)
                self.probe_packet_handler(pkt_data=pkt.data)
        else:
            return

# 获得拓扑 out, in = topo[src_dpid][dst_dpid]
