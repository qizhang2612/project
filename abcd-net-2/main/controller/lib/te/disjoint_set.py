

class DisjointSet(object):
    """Disjoint Set

    Attributes:
        node_info: The node's information, size and parent, but
        the size is meaningful only when the parent is None
    """

    def __init__(self, nodes):
        self.node_info = {}
        for node in nodes:
            self.node_info[node] = {"size": 1, "parent": None}

    def find_parent(self, node):
        if not self.node_info[node]['parent']:
            return node
        ans = self.find_parent(self.node_info[node]['parent'])
        self.node_info[node]['parent'] = ans
        return ans

    def merge(self, node1, node2):
        """Merge two components

        Args:
            node1: One node wanting to be merge
            node2: The other node wanting to be merge
        """
        node1 = self.find_parent(node1)
        node2 = self.find_parent(node2)
        if node1 == node2:
            return False
        if self.node_info[node1]['size'] \
                < self.node_info[node2]['size']:
            node1, node2 = [node2, node1]
        self.node_info[node1]['size'] += self.node_info[node2]['size']
        self.node_info[node2]['parent'] = node1
        return True

    def connected(self, node1, node2):
        """Just two nodes is connected or not

        Args:
            node1: One node wanting to be checked
            node2: The other node wanting to be checked
        """
        node1 = self.find_parent(node1)
        node2 = self.find_parent(node2)
        return node1 == node2
