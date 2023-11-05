# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp
from ryu.lib.packet import ipv4
from collections import defaultdict
from ryu.topology import event
import networkx as nx

from main.controller.manager.traffic_manager import TrafficManager
from main.pub_sub.server.manager.pub_sub_manager import PubSubManager
from main.dir_server.view.controller_view import insert_edges
from main.dir_server.view.controller_view import insert_nodes
from main.dir_server.view.controller_view import clean_topo
from main.controller.lib.te.span_tree import SpanTree

from main.controller.lib.net.topology_info import get_switch_refs_fromco
from main.controller.lib.utils.util import extend_and_unique
from main.controller.lib.net.topology_info import read_static_topo
from main.controller.lib.net.topology_info import read_dynamic_topo

from main.controller.lib.net.packet_handler import handle_arp
from main.controller.lib.net.packet_handler import add_host
from main.controller.lib.net.packet_handler import solve_normal_ipv4_packet


class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.hosts_mac = {}
        self.datapaths = {}

        self.topology_api_app = self
        self.span_tree = SpanTree(self)
        self.hosts_mac = defaultdict(lambda: defaultdict(lambda: None))

        self.get_topo_times = 0
        self.GET_TOPO_limit = 10

        self.node_list = []
        self.edge_list = []

        self.multi_trees = {}
        # {group_ip: {leaf_ip: {'bandwidth': bandwidth, 'delay':delay} } }
        self.topic_sub_demand = {}

        # self.get_topology_info()

    def get_whole_graph(self):
        g = nx.Graph()
        g.add_edges_from(self.edge_list)
        g.add_nodes_from(self.node_list)
        return g

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """Deal with the switch's state changing event

        If some switch enter the network, we just save
        its information into self.datapaths.
        If some switch dead, we just delete its information
        from self.datapaths

        Args:
            ev: the event's reference
        """
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """To install initial flow table into the switch

        Args:
            ev: the event's reference
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, 0, match, actions)

    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, event.EventPortAdd,
                 event.EventPortDelete, event.EventPortModify, event.EventLinkAdd, event.EventLinkDelete])
    def get_topology_info(self, ev):
        """Now we only need the function to get the span tree to
        deal with the arp packet

        Args:
            ev: the event of switch features

        """
        self.get_topo_times = self.get_topo_times + 1
        if self.get_topo_times == 1:
            clean_topo()
        # if self.get_topo_times > self.GET_TOPO_limit:
        #     return
        # switches = get_switch_ports_fromco(self.topology_api_app)
        # edges = get_topo_edges_fromco(self.topology_api_app)

        # switches, edges = read_static_topo()
        switches, edges = read_dynamic_topo(self)
        # self.datapaths = get_switch_refs_fromco(self)
        extend_and_unique(self.node_list, switches)
        extend_and_unique(self.edge_list, edges)

        self.span_tree.clean()
        self.span_tree.build_tree(from_controller=False,
                                  switches=switches,
                                  edges=edges)
        insert_nodes(name_list=[switch_id for switch_id in switches], controller=self)
        insert_edges(edge_list=edges, controller=self)

        self.datapaths = get_switch_refs_fromco(self.topology_api_app)

    @staticmethod
    def _add_flow(datapath,
                  priority, match,
                  actions, buffer_id=None):
        """Add flow to the switch

        Args:
            datapath: the reference of the switch
            priority: the priority of the flow entity
            match: the matching conditions of the flow
            actions: the actions of the flow if matched
            buffer_id: how much of packet will be saved into
                        switch buffer if the packet matched
                        and send out of the switch
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Deal with the packet_in packet

        If the destination IP address is 232.0.0.1,
        it means that the controller got a packet towards
        the directory server

        Args:
            ev: the reference of the event

        """
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        ip = pkt.get_protocol(ipv4.ipv4)
        udp_pkt = pkt.get_protocol(udp.udp)
        # handle pub sub request.
        if ip and udp_pkt and ip.dst == '232.0.0.1':
            add_host(self, eth.src, ip.src, datapath.id, in_port)
            # 1. retrieve cmd from payload[pub, sub, pull, ...].
            pub_sub_cmd = pkt.protocols[-1].decode('utf-8')
            # 2. update dir server
            manager = PubSubManager()
            check_result = manager.check_cmd(pub_sub_cmd, ip)
            if check_result:
                # 3. update route.
                te_result = True
                if manager.msg2tm:
                    traffic_manager = TrafficManager(controller=self)
                    te_result, ans_tree = traffic_manager.solve_msg2tm(msg2tm=manager.msg2tm)

                if te_result:  # It means we find the result
                    manager.pub_sub_handler(pub_sub_cmd, ip)
                else:
                    manager.results = {"status": "failed", "msg": "Can not get the multicast tree!"}
            # 4. build reply packet and emit it.
            reply_msg = manager.build_reply(pkt)
            out_port = in_port
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                      in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=reply_msg.data)
            datapath.send_msg(out)
            return

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            handle_arp(controller=self, msg=msg,
                       datapath=datapath,
                       in_port=in_port, pkt=pkt)
            return
        ipv4_packet_res = False
        if ip:
            ipv4_packet_res = \
                solve_normal_ipv4_packet(controller=self,
                                         msg=msg,
                                         datapath=datapath,
                                         in_port=in_port,
                                         eth_header=eth,
                                         ip_pkt=ip,
                                         has_in_port=False)

        if not ip or not ipv4_packet_res:
            pass






