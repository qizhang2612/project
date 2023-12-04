import networkx as nx
from typing import List
from typing import Set
from typing import Dict
from main.dir_server.view.controller_view import get_topo_nodes_fromdb
from main.dir_server.view.controller_view import get_topo_edges_fromdb
from main.controller.lib.te.disjoint_set import DisjointSet
from main.controller.lib.te.multicast_tree import MulticastTree


class TrafficManager(object):
    """A class to translate pub or sub liked command into
    flow correct flow table and group table

    Attributes:
        graph: The whole topology
        controller: The reference to controller
        db_data: Get the data from database or not
        has_error: If this variable is true, we exit
    """
    def __init__(self, controller=None, db_data: bool = True):
        self.graph = nx.Graph()
        self.controller = controller
        self.has_error = False
        self.db_data = db_data
        self.load_topo()

    def solve_msg2tm(self, msg2tm: Dict = ''):
        """Solve the msg from pub_sub_manager

        Args:
            msg2tm: the msg from pub_sub_manager
            'source_ip'
            'group_ip'
            'op': create_tree, delete_tree, add_leaf, delete_leaf
            'leaf_ip'
        """
        result = True
        ans_tree = None
        if msg2tm['op'] == 'create_tree':
            result, ans_tree = self.build_empty_tree(source_ip=msg2tm['source_ip'],
                                                     group_ip=msg2tm['group_ip'])
        elif msg2tm['op'] == 'add_leaf':
            result, ans_tree = self.add_leaf(group_ip=msg2tm['group_ip'],
                                             leaf_ip=msg2tm['leaf_ip'],
                                             bandwidth=msg2tm['bandwidth'],
                                             delay=msg2tm['delay'])
        elif msg2tm['op'] == 'delete_tree':
            result, ans_tree = self.del_tree(group_ip=msg2tm['group_ip'])
        elif msg2tm['op'] == 'delete_leaf':
            result, ans_tree = self.del_leaf(group_ip=msg2tm['group_ip'], leaf_ip=msg2tm['leaf_ip'])
        return result, ans_tree

    def load_topo(self):
        """Load the topology information from database
        """
        nodes = []
        edges = []
        if self.db_data:
            nodes = get_topo_nodes_fromdb()
            edges = get_topo_edges_fromdb()

        nodes_co = self.controller.node_list
        edges_co = self.controller.edge_list
        nodes.extend(nodes_co)
        edges.extend(edges_co)
        self.graph.add_nodes_from(nodes)
        self.graph.add_edges_from(edges)

    def find_normal_path(self, src: str, dst: str):
        path = []
        visited = set()
        self.dfs(src, dst, path, visited)
        if self.has_error:
            path = []
        return path

    def dfs(self, now, dst, path: List = [], visited: Set = set()) -> True:
        """Find a path by depth first searching

        Args:
            now: The node we are
            dst: The node we want to reach
            path: The path from src to now
            visited: The nodes we have visited
        """
        path.append(now)
        visited.add(now)
        if now == dst:
            return True
        try:
            for adj_node in self.graph[now]:
                if adj_node not in visited:
                    if self.dfs(adj_node, dst, path, visited):
                        return True
        except Exception as e:
            self.has_error = True
            return True
        path.pop()
        return False

    def build_empty_tree(self, source_ip: str, group_ip: str):
        """Create an empty multicast tree

        Args:
            source_ip: The source ip address
            group_ip: The group ip address
        """
        ans_tree = MulticastTree(src_address=source_ip,
                                 group_ip=group_ip,
                                 controller=self.controller)
        self.controller.multi_trees[group_ip] = ans_tree
        return True, ans_tree

    def add_leaf(self, group_ip: str, leaf_ip: str, bandwidth: int, delay: int):
        """Add a leaf node in the multicast tree

        Args:
            group_ip: The group ip address
            leaf_ip: The leaf's ip address
            bandwidth: The bandwidth demand
            delay: The delay demand
        """

        mtree = self.controller.multi_trees[group_ip]
        # Get all the leaves and the demands and recalculate it
        if group_ip not in self.controller.topic_sub_demand:
            self.controller.topic_sub_demand[group_ip] = {}
        self.controller.topic_sub_demand[group_ip][leaf_ip] = \
            {'bandwidth': bandwidth, 'delay': delay}
        leaf_demand = self.controller.topic_sub_demand[group_ip]
        result, ans_tree = self.build_tree(leaf_demand=leaf_demand,
                                           group_ip=group_ip,
                                           graph=self.graph,
                                           root=mtree.root.node_id)
        if result:
            # now we just return the ans_tree
            self.controller.multi_trees[group_ip].remove_flows(priority=233)
            self.controller.multi_trees[group_ip] = ans_tree
            self.controller.multi_trees[group_ip].install_tables(priority=233)
        else:
            self.controller.topic_sub_demand[group_ip].pop(leaf_ip)

        return result, ans_tree

    def del_leaf(self, group_ip: str, leaf_ip: str):
        """Delete a multicast tree's leaf

        Args:
            group_ip: The group ip of the multicast tree
            leaf_ip: The ip of the leaf
        """
        mtree = self.controller.multi_trees[group_ip]
        mtree.remove_flows(priority=233)
        mtree.clean_table()
        mtree.delete_branch(leaf_ip)

        mtree.get_all_table(self.graph)
        mtree.install_tables(priority=233)
        mtree.clean_node()

        self.controller.topic_sub_demand[group_ip].pop(leaf_ip)

        return True, mtree

    def del_tree(self, group_ip):
        """Delete the multicast tree

        Args:
            group_ip: The group ip address of the multicast tree
        """
        mtree = self.controller.multi_trees[group_ip]
        mtree.remove_flows(priority=233)
        self.controller.multi_trees.pop(group_ip)
        if group_ip in self.controller.topic_sub_demand:
            self.controller.topic_sub_demand.pop(group_ip)
        return True, None

    def build_tree(self, leaf_demand: Dict, graph: nx.Graph,
                   root, group_ip):
        """Build a multicast tree according to the leaf_demand

        Args:
            leaf_demand: The demand of all the leaf
            graph: A graph to describe the graph
            root: The root of the tree wanted to be built
            group_ip: The group ip of the multicast tree
        """
        ans_tree = MulticastTree(src_address=root,
                                 group_ip=group_ip,
                                 controller=self.controller)

        now_band_graph = graph.copy()

        no_host_edges = []
        for u in now_band_graph.nodes():
            for v in now_band_graph[u]:
                if type(u) == int and type(v) == int and u > v:
                    no_host_edges.append([u, v])
        leaves = [leaf_id for leaf_id in leaf_demand]

        result = self.try_all_condition(graph, no_host_edges, ans_tree,
                                        now_band_graph, leaf_demand, leaves, root, 0)
        ans_tree.get_all_table(self.graph)

        return result, ans_tree

    def try_all_condition(self, graph, no_host_edges, ans_tree,
                          now_band_graph, demand, leaves, source, now):
        """Try all the condition

        Args:
            graph: The graph of the network
            no_host_edges: Exclude the host edges
            ans_tree: The final multicast_tree
            now_band_graph: Until now, how much bandwidth have we installed on
            every edges
            demand: The demand of all leaves
            leaves: A list represent all leaves
            source: The root of the multicast tree
            now: What node we are dealing
        """
        if now == len(leaves):
            return True
        should_edges = []
        for u in graph[leaves[now]]:
            should_edges.append([leaves[now], u])
        for u in graph[source]:
            should_edges.append([source, u])

        for i in range(1, 2**len(no_host_edges)):
            must_edges = should_edges[0:]
            for j in range(len(no_host_edges)):
                if (i >> j) & 1:
                    must_edges.append(no_host_edges[j])
            # Judge whether the edges is a legal path
            if self.check(must_edges, source, leaves[now],
                          now_band_graph, demand[leaves[now]]):
                # try the next leaf
                if self.try_all_condition(graph, no_host_edges, ans_tree,
                                          now_band_graph, demand,
                                          leaves, source, now + 1):
                    ans_tree.add_path_from_edges(must_edges, source, leaves[now])
                    return True
                # if the condition is not ok, we should recover
                # the now_band_graph
                else:
                    for edge in must_edges:
                        now_band_graph[edge[0]][edge[1]]['bandwidth'] \
                            += demand[leaves[now]]['bandwidth']
        return False

    def check(self, must_edges, source, leaf,
              now_band_graph, demand):
        """Check the path is ok or not

        Args:
            must_edges: The path want to check
            source: The source of the path
            leaf: The destination of the path
            now_band_graph: The current bandwidth of the graph
            demand: The flow's demand, including bandwidth and delay
        """
        dsu = DisjointSet(now_band_graph.nodes())
        has_added = []
        flag = True
        tot_delay = 0
        for edge in must_edges:
            if not dsu.merge(edge[0], edge[1]):
                flag = False
                break
            now_band_graph[edge[0]][edge[1]]['bandwidth'] \
                -= demand['bandwidth']
            has_added.append(edge)
            tot_delay += \
                now_band_graph[edge[0]][edge[1]]['delay']

            # The bandwidth is not satisfied
            if now_band_graph[edge[0]][edge[1]]['bandwidth'] < 0:
                flag = False
                break

            # The bandwidth is not satisfied
            if tot_delay > demand['delay']:
                flag = False
                break

        if flag and dsu.connected(source, leaf):
            return True
        else:
            for added_edge in has_added:  # recover the left bandwidth
                now_band_graph[added_edge[0]][added_edge[1]]['bandwidth'] \
                    += demand['bandwidth']
        return False

