from typing import List
from typing import Dict
import networkx as nx
import sys


from main.controller.lib.te.sdn_node import SdnNode


class TableManager(object):
    """Table manager is used to install flow entities or group table
    """

    def __init__(self, controller=None):
        self.controller = controller
        pass

    @staticmethod
    def _add_action(entity, parser):
        """Translate the action into Openflow action

        Args:
             entity: The item wanted to be translated
             parser: Openflow1.3 parser
        """
        actions = []
        if 'OFPActionSetField' in entity['action']:
            action = [
                parser.OFPActionSetField(ipv4_dst=
                                         entity['action']['OFPActionSetField'])]
            actions.extend(action)
        if 'OFPActionOutput' in entity['action']:
            action = [
                parser.OFPActionOutput(entity['action']['OFPActionOutput'])]
            actions.extend(action)
        if 'OFPActionGroup' in entity['action']:
            action = [parser.OFPActionGroup(group_id=
                                            entity['action']['OFPActionGroup'])]
            actions.extend(action)
        if not actions:
            raise Exception("No output action")
        return actions

    @staticmethod
    def _add_flow_table(datapath, node: SdnNode, match_type: str, has_in_port: bool = True,
                        priority=100):
        """Add flow table to the network
        Add the assign tree node's flow table to the network

        Args:
            datapath: The reference of the switches
            node: The flow table's information
            priority: The priority of the flow entity
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for in_port in node.flow_table:
            flow_entity = node.flow_table[in_port]
            if match_type == 'arp':
                if has_in_port:
                    match = parser.OFPMatch(in_port=in_port,
                                            arp_tpa=flow_entity['match']['arp_tpa'],
                                            arp_spa=flow_entity['match']['arp_spa'],
                                            eth_type=0x0806)
                else:
                    match = parser.OFPMatch(arp_tpa=flow_entity['match']['arp_tpa'],
                                            arp_spa=flow_entity['match']['arp_spa'],
                                            eth_type=0x0806)
            elif match_type == 'ipv4':
                if has_in_port:
                    match = parser.OFPMatch(in_port=in_port,
                                            ipv4_src=flow_entity['match']['ipv4_src'],
                                            ipv4_dst=flow_entity['match']['ipv4_dst'],
                                            eth_type=0x800)
                else:
                    match = parser.OFPMatch(ipv4_src=flow_entity['match']['ipv4_src'],
                                            ipv4_dst=flow_entity['match']['ipv4_dst'],
                                            eth_type=0x800)
            actions = TableManager._add_action(flow_entity, parser)
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = parser.OFPFlowMod(datapath=datapath, match=match,
                                    command=ofproto.OFPFC_ADD,
                                    idle_timeout=0, hard_timeout=0,
                                    priority=priority, instructions=inst)
            datapath.send_msg(mod)

    @staticmethod
    def _get_buckets(group_entity, parser):
        """A function to translate the node's buckets into Openflow buckets

        Args:
            group_entity: The group_entity in node
            parser: The parser
        """
        buckets = group_entity['buckets']
        parser_buckets = []
        for bucket in buckets:
            actions = TableManager._add_action(bucket, parser)
            parser_bucket = parser.OFPBucket(actions=actions)
            parser_buckets.append(parser_bucket)
        return parser_buckets

    @staticmethod
    def _add_group_table(datapath, node: SdnNode, match_type: str = '', has_in_port: bool = True):
        """Add group table to the network
        Add the assign tree node's group table to the network

        Args:
            datapath: The reference of the switches
            node: The flow table's information
            match_type: In fact we don't use it
            has_in_port: In fact we don't use it
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for in_port in node.group_table:
            # add group table
            group_table_id = node.group_table[in_port]['id']
            group_entity = node.group_table[in_port]
            buckets = group_entity['buckets']
            parser_buckets = []
            for bucket in buckets:
                actions = TableManager._add_action(bucket, parser)
                parser_bucket = parser.OFPBucket(actions=actions)
                parser_buckets.append(parser_bucket)

            mod = parser.OFPGroupMod(
                datapath=datapath,
                command=ofproto.OFPGC_ADD,
                type_=ofproto.OFPGT_ALL,
                group_id=group_table_id,
                buckets=parser_buckets)
            datapath.send_msg(mod)

    def translate_path(self, graph: nx.Graph, path: List = [],
                       switches: Dict = {}, road_type: str = 'ipv4',
                       has_in_port=True):
        """Translate from path list to flow entities

        Args:
            graph: The graph of the network
            path: A list containing all the the nodes
            switches: A dict containing all the switches' reference
            road_type: arp or ipv4
            has_in_port: Add in_port or not in match
        """
        if not path:
            return
        for index in range(2):
            pre_node = SdnNode(node_id=path[0], parent={})
            for i in range(1, len(path)-1):
                cur_node = SdnNode(node_id=path[i], parent={})
                nxt_node = SdnNode(node_id=path[i+1], parent={})
                # generate new table
                # self.del_flow_table(cur_node)
                in_port_info = graph[cur_node.node_id][pre_node.node_id]['port']
                in_port = in_port_info[cur_node.node_id]
                cur_node.flow_table[in_port] = {"match": {}, "action": {}}
                flow_entity = cur_node.flow_table[in_port]
                if road_type == 'arp':
                    flow_entity['match']['arp_tpa'] = path[-1]
                    flow_entity['match']['arp_spa'] = path[0]
                elif road_type == 'ipv4':
                    flow_entity['match']['ipv4_src'] = path[0]
                    flow_entity['match']['ipv4_dst'] = path[-1]
                else:
                    print('wrong road_type')
                    sys.exit(-1)

                out_port_info = graph[cur_node.node_id][nxt_node.node_id]['port']
                flow_entity['action']['OFPActionOutput'] = \
                    out_port_info[cur_node.node_id]

                self._add_flow_table(datapath=switches[cur_node.node_id],
                                     node=cur_node,
                                     match_type=road_type,
                                     has_in_port=has_in_port)
                pre_node = cur_node
            path.reverse()
        return True

    def del_total_table(self, node: SdnNode, priority=100):
        """Delete the node's group table

        Args:
            node: The node we want to delete all the group flows in it.
            priority: The priority of the flow table
        """
        # delete proactive flow table
        datapath = self.controller.datapaths[node.node_id]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for in_port in node.flow_table:
            flow_entity = node.flow_table[in_port]
            match = parser.OFPMatch(in_port=in_port,
                                    ipv4_src=flow_entity['match']['ipv4_src'],
                                    ipv4_dst=flow_entity['match']['ipv4_dst'],
                                    eth_type=0x800)
            out_port = 0
            out_group = 0
            if 'OFPActionOutput' in flow_entity['action']:
                out_port = flow_entity['action']['OFPActionOutput']
            elif 'OFPActionGroup' in flow_entity['action']:
                out_group = flow_entity['action']['OFPActionGroup']

            # Example:
            # mod = parser.OFPFlowMod(datapath, 0, 0, 0, ofproto.OFPFC_DELETE, 0, 0, 2,
            #                         ofproto.OFP_NO_BUFFER, out_port, ofproto.OFPG_ANY,
            #                         ofproto.OFPFF_SEND_FLOW_REM, match=match)
            mod = parser.OFPFlowMod(datapath=datapath, cookie=0, cookie_mask=0, table_id=0,
                                    command=ofproto.OFPFC_DELETE,
                                    idle_timeout=0, hard_timeout=0,
                                    priority=priority, buffer_id=ofproto.OFP_NO_BUFFER,
                                    out_port=out_port, out_group=ofproto.OFPG_ANY,
                                    flags=ofproto.OFPFF_SEND_FLOW_REM, match=match)
            datapath.send_msg(mod)

        for in_port in node.group_table:
            group_id = node.group_table[in_port]['id']
            mod = parser.OFPGroupMod(
                datapath=datapath,
                command=ofproto.OFPGC_DELETE,
                type_=ofproto.OFPGT_ALL,
                group_id=group_id)
            datapath.send_msg(mod)

    def install_entity(self, node: SdnNode, priority=100):
        """Install flow entity and group entity for some node

        Args:
            node: The node, who wants to install entity
            priority: The priority of the entity
        """
        if node.is_host:
            return
        self._add_group_table(datapath=self.controller.datapaths[node.node_id],
                              node=node,
                              match_type='ipv4',
                              has_in_port=True)
        self._add_flow_table(self.controller.datapaths[node.node_id],
                             node=node,
                             match_type='ipv4',
                             has_in_port=True,
                             priority=priority)


