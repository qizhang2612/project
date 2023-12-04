from collections import defaultdict


class SdnNode:
    """A node class, which can be used as node in multicast tree,
    including group table, flow table, children, parent, node id, and is_host

    Attributes:
        group_table: group table of the node
        flow_table: flow table of the node
        children: children of the node
        node_id: equal to dpid, node id of the node, unique in the tree
        pre_node: mapping pre_node_id to a pre node
        tree_parent: mapping the leaf ip to a pre node
    """

    def __init__(self, node_id, parent={}) -> None:
        self.group_table = defaultdict(lambda: {'buckets': []})
        self.flow_table = defaultdict(lambda: {'match': {}, 'action': {}})
        self.node_id = node_id
        self.pre_node = {}
        self.children = {}
        self.tree_parent = {}
        self.is_host = False

    def clean_table(self):
        self.group_table = defaultdict(lambda: {'buckets': []})
        self.flow_table = defaultdict(lambda: {'match': {}, 'action': {}})
