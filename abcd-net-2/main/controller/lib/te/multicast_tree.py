import networkx as nx
from random import random
from collections import defaultdict
from main.controller.lib.te.sdn_node import SdnNode
from main.controller.lib.te.reserve_information import ReserveInformation
from main.controller.manager.table_manager import TableManager


class MulticastTree:
    """tree class of multicast tree

    tree model of multicast tree, start from one origin, construct a tree graph using shortest path to reach each listener,
    and avoid loop.

    Attributes:
        root: root of the tree
        nodes: nodes in the tree
        leaf_nodes: leaf nodes in the tree
        tree_graph: tree graph of the tree
        network_graph: network graph of the network, used to find shortest path and link port datapath instance

    """

    def __init__(
            self,
            controller,
            group_ip: str,
            src_address: str,
            reserve_info: ReserveInformation = None,
            **kwargs) -> None:
        self.root = SdnNode(node_id=src_address, parent={})
        self.root.is_host = True
        self.src_address = src_address
        self.nodes = {src_address: self.root}
        self.group_ip = group_ip
        self.controller = controller
        self.table_manager = TableManager(controller)

    def remove_flows(self, priority=233):
        """Remove all the flows in the multicast tree
        """
        for node_id in self.nodes:
            node = self.nodes[node_id]
            if not node.is_host:
                self.table_manager.del_total_table(node, priority=priority)

    def clean_table(self):
        for node_id in self.nodes:
            node = self.nodes[node_id]
            node.group_table = defaultdict(lambda: {'buckets': []})
            node.flow_table = defaultdict(lambda: {'match': {}, 'action': {}})

    def get_path_from_branch(self, branch, source, leaf):
        """Get the complete path from the branch graph

        Args:
            branch: The branch graph
            source: The source node
            leaf: The leaf node
        """
        now = source
        pre_vis = None
        path = []
        found_next = True
        while found_next:
            path.append(now)
            found_next = False
            for nxt in branch[now]:
                if nxt == pre_vis:
                    continue
                else:
                    found_next = True
                    pre_vis = now
                    now = nxt
                    break
        return path

    def add_path_from_edges(self, must_edges: [], source, leaf):
        """Add a path into the multicast tree by
        a list of edges

        Args:
            must_edges: The edges should be add
            source: The source of the path
            leaf: The destination of the path
        """
        branch = nx.Graph()
        edges = []
        for edge in must_edges:
            edges.append((edge[0], edge[1]))
        branch.add_edges_from(edges)

        # [src, s1, s2 ... ,dst]
        path = self.get_path_from_branch(branch, source, leaf)
        # [dst, ...s2, s1 ,src]
        path.reverse()
        for name in path:
            if name not in self.nodes:
                self.nodes[name] = SdnNode(node_id=name, parent={})
        child = self.nodes[leaf]
        child.is_host = True
        for i in range(1, len(path)):
            now_node_id = path[i]
            now_node = self.nodes[now_node_id]
            now_node.children[child.node_id] = child
            child.pre_node[now_node_id] = now_node
            child.tree_parent[leaf] = now_node

            child = now_node

    def get_table(self, count_table, now_node, graph):
        """Use the information to rebuild the count_table

        Args:
            count_table: The tool to build flow table and group table
            now_node: The now node, who wants to be made flow and group table
            graph: The graph of the network
        """
        for parent_id in count_table:
            in_port = graph[parent_id][now_node.node_id]['port'][now_node.node_id]
            total_child = list(count_table[parent_id].keys())
            cnt_child = len(total_child)

            # There is only one flow entity
            if cnt_child == 1:
                child = self.nodes[total_child[0]]
                out_port = graph[now_node.node_id][child.node_id]['port'][now_node.node_id]
                now_node.flow_table[in_port]['match']['ipv4_src'] = self.src_address
                now_node.flow_table[in_port]['match']['ipv4_dst'] = self.group_ip
                now_node.flow_table[in_port]['action']['OFPActionOutput'] = out_port

                if child.is_host:
                    now_node.flow_table[in_port]['action']['OFPActionSetField']\
                        = child.node_id
            # There should be a group table
            else:
                group_table_id = int(10000 * random())
                now_node.flow_table[in_port]['match']['ipv4_src'] = self.src_address
                now_node.flow_table[in_port]['match']['ipv4_dst'] = self.group_ip
                now_node.flow_table[in_port]['action']['OFPActionGroup'] = group_table_id
                now_node.group_table[in_port]['id'] = group_table_id
                for child_id in total_child:
                    bucket = {}
                    child = self.nodes[child_id]
                    out_port = graph[now_node.node_id][child.node_id]['port'][now_node.node_id]
                    bucket['action'] = {'OFPActionOutput': out_port}
                    if child.is_host:
                        bucket['action']['OFPActionSetField'] = child.node_id
                    now_node.group_table[in_port]['buckets'].append(bucket)

    def get_all_table(self, graph):
        for node_id in self.nodes:
            now_node = self.nodes[node_id]
            if now_node.is_host:
                continue
            count_table = {}
            for parent in now_node.pre_node:
                count_table[parent] = {}
            for child_id in now_node.children:
                child_node = now_node.children[child_id]
                for child_leaf in child_node.tree_parent:
                    if child_node.tree_parent[child_leaf].node_id \
                            == now_node.node_id:
                        two_up_parent = child_node. \
                            tree_parent[child_leaf].tree_parent[child_leaf]
                        if child_id not in count_table[two_up_parent.node_id]:
                            count_table[two_up_parent.node_id][child_id] = []
                        count_table[two_up_parent.node_id][child_id].append(child_leaf)
            now_node.clean_table()
            self.get_table(count_table, now_node, graph)

    def install_tables(self, priority=100):
        """According to the information on every
        nodes, we install the flow entity and group entity

        Args:
            priority: The priority of the flow table
        """
        for node_id in self.nodes:
            node = self.nodes[node_id]
            self.table_manager.install_entity(node, priority=priority)

    def clean_node(self):
        tot_node_id = list(self.nodes.keys())
        for node_id in tot_node_id:
            now_node = self.nodes[node_id]
            if now_node == self.root:
                continue
            if not now_node.children and not now_node.pre_node:
                self.nodes.pop(node_id)

    def delete_branch(self, leaf_ip):
        """Delete a branch of the multicast tree

        Args:
            leaf_ip: The leaf ip of the multicast tree
        """

        now_node = self.nodes[leaf_ip]

        while now_node.node_id != self.root.node_id:
            parent_node = now_node.tree_parent[leaf_ip]
            now_node.tree_parent.pop(leaf_ip)

            save_pre_node = False
            for bottom_leaf in now_node.tree_parent:
                if now_node.tree_parent[bottom_leaf].node_id \
                        == parent_node.node_id:
                    save_pre_node = True

            if not save_pre_node:
                now_node.pre_node.pop(parent_node.node_id)
                parent_node.children.pop(now_node.node_id)

            now_node = parent_node





