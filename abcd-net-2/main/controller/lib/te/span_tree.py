import networkx as nx
from main.controller.lib.net.topology_info import get_topo_edges_fromco
from main.controller.lib.net.topology_info import get_switch_ports_fromco
from queue import Queue


class SpanTree(object):
    """If the topology has cycle, we need to find a span tree to only
    flood on these ports

    Attributes:
        switches: A dict containing all the switches
        graph: The abstract topology
        in_ports: A dict containing all the switches' baned port
        controller: The controller's reference
    """
    def __init__(self, controller):
        self.controller = controller
        self.switches = []
        self.graph = nx.Graph()
        self.in_ports = {}
        self.root = -1
        self.empty = False

    def get_topo_info(self, switches: list = [],
                      edges: list = [], from_controller: bool = True):
        """Get the topology's information

        Args:
            switches: A list containing all the switches
            edges: A list containing all the edges
            from_controller: If we want to get data from controller,
                            it will bre true. Otherwise, it will be False, and
                            we pass the switches, edges
        """
        if from_controller:
            self.switches = get_switch_ports_fromco(self.controller)
            edges = get_topo_edges_fromco(self.controller)
        else:
            self.switches = switches
        switch_ids = [switch_id for switch_id in self.switches]
        if switch_ids:
            self.root = switch_ids[0]
        else:
            self.empty = True
        self.graph.add_nodes_from(switch_ids)
        self.graph.add_edges_from(edges)
        self.in_ports = {}
        for switch_id in switch_ids:
            self.in_ports[switch_id] = set(self.switches[switch_id])

    def build_tree(self, switches: list = [],
                   edges: list = [], from_controller: bool = True):
        """Build the span tree to forbid the flood

        Args:
            switches: A list containing all the switches
            edges: A list containing all the edges
            from_controller: If we want to get data from controller,
                            it will bre true. Otherwise, it will be False, and
                            we pass the switches, edges
        """
        self.get_topo_info(from_controller=from_controller,
                           switches=switches, edges=edges)
        if not self.empty:
            self.bfs()

    def delete_port(self, node1, node2):
        """Delete the edge (node1, node2)'s port

        Args:
            node1: A node in graph
            node2: Another node in graph
        """
        del_port1 = self.graph[node1][node2]['port'][node1]
        del_port2 = self.graph[node1][node2]['port'][node2]
        if del_port1 in self.in_ports[node1] and del_port2 in \
                self.in_ports[node2]:
            self.in_ports[node1].remove(del_port1)
            self.in_ports[node2].remove(del_port2)

    def bfs(self):
        """Use bfs to find a span tree
        """
        q = Queue()
        q.put(self.root)
        parent_id = {self.root: self.root}
        while not q.empty():
            now = q.get()
            for child_node in self.graph[now]:
                if child_node in parent_id and parent_id[now] != child_node:
                    self.delete_port(child_node, now)
                elif child_node not in parent_id:
                    q.put(child_node)
                    parent_id[child_node] = now

    def clean(self):
        """Clean the information
        """
        self.switches = []
        self.graph = nx.Graph()
        self.in_ports = {}
        self.root = -1
        self.empty = False







