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
from ryu.controller.handler import CONFIG_DISPATCHER
from flow_mod import FlowMod
from netstate_config import *
import time
import networkx
import copy

#PACKET_LOSS_DETECT_MAC_SRC = "00:f1:f3:1a:09:8c"
#PACKET_LOSS_DETECT_MAC_DST = "00:f1:f3:19:37:b2"
#不能用真实的
PACKET_LOSS_DETECT_MAC_SRC = "a2:53:30:97:f9:63"
PACKET_LOSS_DETECT_MAC_DST = "06:03:18:58:fb:73"
PACKET_LOSS_DETECT_SRC = "10.0.0.111"
PACKET_LOSS_DETECT_DST = "10.0.0.222"
DETECT_PACKET_NUM = 100

class PacketLossDetect(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):

        super().__init__(*_args, **_kwargs)
        self.name = app_packet_loss_detect_name
        self.flow_mod = FlowMod()
        self.link_to_port = {}
        self.datapaths = {}
        self.graph = networkx.graph.Graph()
        self.switch_port_table = {}
        self.num = 0
        self.drop_num = {}
        self.packet_loss_detect_thread = hub.spawn(self._packet_loss_detect)

        # 依赖topology生成的网络拓扑
        self.app_topology = app_manager.lookup_service_brick(app_topology_name)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handle(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

    def _construct_detect_packet(self):
        e = ethernet.ethernet(dst=PACKET_LOSS_DETECT_MAC_SRC, src=PACKET_LOSS_DETECT_MAC_DST, ethertype=ether.ETH_TYPE_IP)
        ip = ipv4.ipv4(src=PACKET_LOSS_DETECT_SRC, dst=PACKET_LOSS_DETECT_DST, proto=IPPROTO_UDP)
        udp_ = udp.udp(src_port=6666, dst_port=8888)
        pkt = packet.Packet()
        pkt.add_protocol(e)
        pkt.add_protocol(ip)
        pkt.add_protocol(udp_)
        pkt.serialize()
        return pkt

    def send_flow_mod(self, switch_list, port_list):
        # send flow mod
        datapaths = self.datapaths
        for i in range(len(switch_list)):
            in_port, out_port = port_list[i]
            #self.logger.info(in_port)
            #self.logger.info(out_port)
            if datapaths.get(switch_list[i]):
                datapath = datapaths[switch_list[i]]
            else:
                self.logger.info("unknown dpid in link")
                return
            ofproto = datapath.ofproto
            if i == len(switch_list) - 1:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=PACKET_LOSS_DETECT_SRC, dst_ip=PACKET_LOSS_DETECT_DST,
                                               in_port=in_port, out_port=ofproto.OFPP_CONTROLLER)
            elif i == 0:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=PACKET_LOSS_DETECT_SRC, dst_ip=PACKET_LOSS_DETECT_DST,
                                               in_port=ofproto.OFPP_CONTROLLER, out_port=out_port)
            else:
                self.flow_mod.send_flow_mod_ip(datapath=datapath, src_ip=PACKET_LOSS_DETECT_SRC, dst_ip=PACKET_LOSS_DETECT_DST,
                                               in_port=in_port, out_port=out_port)                
        # 睡眠，保证在流表下发之后探测包才被下发到交换机中
        time.sleep(0.05)

    def send_detect_packet(self,switch_list):
        # send detect packet
        pkt = self._construct_detect_packet()
        datapath = self.datapaths[switch_list[0]]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=ofproto.OFPP_TABLE)]
        msg = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions, data=pkt)
        datapath.send_msg(msg)

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
    
    def get_neighbors(self, dpid):
        '''
        获得邻居交换机节点号码
        '''  
        return networkx.all_neighbors(self.graph, dpid)

    def _packet_loss_detect(self):
        hub.sleep(15)
        self.graph = copy.deepcopy(self.app_topology.graph)
        self.link_to_port = copy.deepcopy(self.app_topology.link_to_port)
        self.switch_port_table = copy.deepcopy(self.app_topology.switch_port_table)
        while True:
            hub.sleep(5)
            for dpid in self.datapaths.keys():
                for nb_dpid in self.get_neighbors(dpid):
                    self.num = 0
                    switch_list = [dpid,nb_dpid]
                    port_list = self._get_port_list(switch_list)
                    self.send_flow_mod(switch_list,port_list)
                    for i in range(DETECT_PACKET_NUM):
                        self.send_detect_packet(switch_list)
                    hub.sleep(5)
                    self.drop_num[(dpid,nb_dpid)] = self.num
                    self.logger.info(self.drop_num)
                for link in self.drop_num.keys():
                    packet_loss_ratio =  (DETECT_PACKET_NUM - self.drop_num[link]) / DETECT_PACKET_NUM
                    dpid1 = link[0]
                    dpid2 = link[1]
                    #self.logger.info(packet_loss_ratio)
                    db_result = "从交换机"+str(dpid1)+"到交换机"+str(dpid2)\
                                +"发送"+str(DETECT_PACKET_NUM)+"个探测包的丢包率为"\
                                +str(packet_loss_ratio)
                    self.logger.info(db_result)
                    

                    

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        ip_header = pkt.get_protocol(ipv4.ipv4)
        if ip_header:
            src_ip, dst_ip = ip_header.src, ip_header.dst
            if src_ip == PACKET_LOSS_DETECT_SRC and dst_ip == PACKET_LOSS_DETECT_DST:
                #self.logger.info("recv packetloss detect packet")
                self.num = self.num + 1
        else:
            return
