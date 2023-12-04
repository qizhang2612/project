from ryu.topology.api import get_switch, get_link
from typing import List
from typing import Dict
import json


STATIC_TOPO_JSON_PATH = './main/controller/conf/static_topo.json'
MAX_PORT = 2000


def get_switch_ports_fromco(controller) -> Dict:
    """Get a controller's controlled switches' port information

    Args:
        controller: The class referring to the controller

    Returns:
        [{'dpid': '1', 'ports':[1,2,3...]}, {'dpid': '2', 'ports':[1,2,3...]} ...]
    """
    switch_list = get_switch(controller, None)
    switch_info = {}
    for switch in switch_list:
        item = {}
        ports = []
        dpid = -1
        for port in switch.ports:
            if port.port_no <= MAX_PORT:
                ports.append(port.port_no)
                dpid = port.dpid
        if dpid != -1:
            switch_info[dpid] = ports

    # Now, we use the static data
    # switch_info = read_static_topo()[0]
    return switch_info


def get_switch_refs_fromco(controller) -> Dict:
    """Get a controller's controlled switches' reference

    Args:
        controller: The class referring to the controller
    """
    switch_list = get_switch(controller, None)
    switch_refs = {}
    for switch in switch_list:
        switch_refs[switch.dp.id] = switch.dp

    return switch_refs


def get_topo_edges_fromco(controller) -> List:
    """Get a controller's controlled switches' link information

    Args:
        controller: The class referring to the controller

    Returns:
        [(1, 2, {"port": port_info}) ,(1, 3, {"port": port_info})]
    """

    edges = []
    edges_list = get_link(controller, None)
    for edge in edges_list:
        port_info = {edge.src.dpid: edge.src.port_no, edge.dst.dpid: edge.dst.port_no}
        edge_info = (edge.src.dpid, edge.dst.dpid, {'port': port_info, 'bandwidth': 10, 'delay': 0})
        edges.append(edge_info)

    # now we must use the static data
    # edges = read_static_topo()[1]
    return edges


def read_static_topo():
    """Read the static topo from json file
    """
    with open(STATIC_TOPO_JSON_PATH, 'r') as fp:
        d = json.load(fp)
    switches = {}
    edges = []

    for sw_id in d['nodes']:
        switches[int(sw_id)] = d['nodes'][sw_id]

    for entity in d['edges']:
        src = entity[0]
        dst = entity[1]
        src_port = entity[2]['port'][str(src)]
        dst_port = entity[2]['port'][str(dst)]
        bandwidth = entity[2]['bandwidth']
        delay = entity[2]['delay']
        port_info = {"port": {src: src_port, dst: dst_port},
                     "bandwidth": bandwidth, "delay": delay}
        edges.append((src, dst, port_info))
    return switches, edges


def read_dynamic_topo(controller):
    """Get the dynamic topology

    Args:
        controller: The reference of controller
    """
    edges = get_topo_edges_fromco(controller)
    switches = get_switch_ports_fromco(controller)
    return switches, edges


def get_topo_edges_fromfile():
    """Get the topo edges from files
    """
    edges = read_static_topo()[1]
    return edges


def get_switch_ports_fromfile():
    """Get the topo nodes from files
    """
    switch_info = read_static_topo()[0]
    return switch_info
