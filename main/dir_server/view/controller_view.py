from main.dir_server.data_provider.data_provider import DataProvider
from typing import Dict
from typing import List
import sys


CONTROLLER_YAML_PATH = './main/dir_server/conf/server_config.yaml'
PORT_LIMIT = 100


def get_all_paths_fromdb():
    """Get all path's names

    Returns:
        A list contains all paths' name like topicXsubscriber
    """
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    paths = data_provider.get("paths")
    result = paths if paths else []
    return result


def get_path_fromdb(topic_name: str, subscriber: str) -> Dict:
    """Get path's information including nodes, delay and bandwidth

    Args:
        topic_name: the topic's name
        subscriber: the subscriber's name
    Returns:
        The path's information
    """
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    path_name = 'path_' + topic_name + 'X' + subscriber
    path_info = data_provider.get(path_name)
    result = path_info if path_info else {}
    return result


def get_topo_nodes_fromdb() -> List[str]:
    """Get the network's all nodes

    Returns:
        A list contains all the topo nodes, which are found so far
    """
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    toponodes = data_provider.get('toponodes')
    result = []
    for node in toponodes:
        result.append(recover_from_dbname(node))
    return result


def get_topo_edge_fromdb(src: str, dst: str) -> Dict:
    """Get some link defined by (src, to)

    Returns:
        A dict represent an edge
    """
    src = trans2dbname(src)
    dst = trans2dbname(dst)
    src_dst = "topoedge" + "_" + src + "X" + dst
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    edge = data_provider.get(src_dst)
    result = edge if edge else {}
    if result:
        result['src_port'] = int(result['src_port'])
        result['dst_port'] = int(result['dst_port'])
        result['bandwidth'] = float(result['bandwidth'])
        result['delay'] = float(result['delay'])
    return result


def get_topo_edges_fromdb() -> List:
    """Get the network's all edges

    Returns:
        A list contains all the edges, which are found so far
        [ {"src": src, "dst": to, "port":{src: src_port, dst: dst_port} } ]
    """
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    edges = data_provider.get('topoedges')
    result = []
    for src_dst in edges:
        src, dst = src_dst.split('X')
        port_info = get_topo_edge_fromdb(src, dst)
        src = recover_from_dbname(src)
        dst = recover_from_dbname(dst)
        edge = (src, dst,
                {"port": {src: port_info['src_port'],
                          dst: port_info['dst_port']},
                 "bandwidth": port_info['bandwidth'],
                 "delay": port_info['delay']})
        result.append(edge)
    return result


def get_topo_edges_total_info_fromdb():
    """Get the network's all edges for front.

    Returns:
        A list contains all the edges, which are found so far
        [(src, dst)...]
    """
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    edges = data_provider.get('topoedges')
    result = []
    for src_dst in edges:
        src, dst = src_dst.split('X')
        port_info = get_topo_edge_fromdb(src, dst)
        edge = {"src": src, "dst": dst,
                "bandwidth": port_info['bandwidth'],
                "delay": port_info['delay']}
        result.append(edge)
    return result


def insert_edge(controller=None, src: str = '', dst: str = '',
                src_port: int = 0, dst_port: int = 0,
                check: bool = True, bandwidth: float = 100, delay: float = 0):
    """Add edge into the database

    Args:
        controller: A reference to controller
        src: The from node
        dst: The to node
        src_port: The from node's port
        dst_port: The to node's port
        check: Whether check the element exists or not
        bandwidth: The bandwidth of the link
        delay: The delay of the link
    """

    if src_port > PORT_LIMIT \
            or dst_port > PORT_LIMIT:
        print('Wrong port number')
        return
    edge_mm = (src, dst,
               {"port": {src: src_port, dst: dst_port},
                "bandwidth": bandwidth,
                "delay": delay})
    src = trans2dbname(src)
    dst = trans2dbname(dst)
    data_provider = DataProvider(config_path=CONTROLLER_YAML_PATH)
    src_dst = src + 'X' + dst
    if check:
        res = data_provider.get('topoedge' + '_' + src_dst)
        if res:  # It means that we have got the edge
            return
    data_provider.insert('topoedges', (src_dst, src_port, dst_port, bandwidth, delay))
    if edge_mm not in controller.edge_list and controller:
        controller.edge_list.append(edge_mm)


def insert_node(controller=None, name: str = '', check: bool = True):
    """insert node into the database

    Args:
        controller: The reference to controller
        name: Node's name
        check: Whether check the element exists or not
    """
    # this is a switch
    if type(name) == int and name <= 0:
        print('wrong in Database')
        return
    node_mm = name
    name = trans2dbname(name)

    data_provider = DataProvider(CONTROLLER_YAML_PATH)
    if check:
        nodes = data_provider.get('toponodes')
        if name in nodes:
            return

    data_provider.insert('toponodes', '(\'' + name + '\')')

    if controller and node_mm not in controller.node_list:
        controller.node_list.append(node_mm)


def trans2dbname(name: str):
    """We use the function transfer str to str
    and int(the dpid) into 's' + str(name)
    """
    if type(name) == int:
        return 's' + str(name)
    return name


def recover_from_dbname(name: str):
    """We use the function recover the str to str
    and switch name such as s1 into int(1)
    """
    if name:
        if name.startswith('s'):
            return int(name[1:])
    return name


def insert_nodes(controller=None, name_list: List = []):
    """Insert much name into the database

    Args:
        controller: The reference to controller
        name_list: A list containing all the nodes
    """
    data_provider = DataProvider(CONTROLLER_YAML_PATH)
    now_name_list = data_provider.get('toponodes')
    for name in name_list:
        if trans2dbname(name) not in now_name_list:
            insert_node(controller=controller, name=name,
                        check=False)


def insert_edges(controller=None, edge_list: List = []):
    """Insert many edges into the database

    Args:
        controller: A reference to controller
        edge_list: A list containing all the edges
    """
    data_provider = DataProvider(CONTROLLER_YAML_PATH)
    now_edge_list = data_provider.get('topoedges')

    for item in edge_list:
        src = item[0]
        dst = item[1]
        src_port = item[2]['port'][src]
        dst_port = item[2]['port'][dst]
        bandwidth = item[2]['bandwidth']
        delay = item[2]['delay']
        src_dst = trans2dbname(src) + 'X' + trans2dbname(dst)
        if src_dst not in now_edge_list:
            insert_edge(controller=controller,
                        src=src, dst=dst,
                        src_port=src_port, dst_port=dst_port,
                        check=False, bandwidth=bandwidth,
                        delay=delay)


def clean_topo():
    """Clean the database's data
    """
    data_provider = DataProvider(CONTROLLER_YAML_PATH)
    data_provider.delete('toponodes')
    data_provider.delete('topoedges')
