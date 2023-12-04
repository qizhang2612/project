from flask import Flask
from flask import jsonify
from flask_cors import CORS
import yaml
from typing import Dict
from random import randint

from main.dir_server.view.server_view import get_topics
from main.dir_server.view.server_view import get_sub_list
from main.dir_server.view.server_view import get_topic_info
from main.dir_server.view.server_view import get_hosts
from main.dir_server.view.server_view import get_host_info
from main.dir_server.view.controller_view import get_topo_nodes_fromdb
from main.dir_server.view.controller_view import get_topo_edges_total_info_fromdb


app = Flask(__name__)
cors = CORS(app)
HOST_IP = '127.0.0.1'
HOST_PORT = 5000

CONFIG_PATH = './main/pub_sub/server/web/conf/front_end.yaml'


def get_dict(router: str):
    """Get the dict and index list by a router

    Args:
        router: A string representing the router
    """
    result = read_yaml(CONFIG_PATH)[router]
    result['data'] = []
    indexes = []
    for item in result["columns"]:
        indexes.append(item["dataIndex"])
    return result, indexes


def read_yaml(config_path: str = CONFIG_PATH):
    """Read an yaml file

    Args:
        config_path: A string representing the configure file path
    """
    with open(config_path, "r") as fp:
        config = yaml.load(fp, Loader=yaml.FullLoader)
    return config


@app.route('/relationships', methods=['GET'])
def get_pub_sub_relations():
    """Return the pub_sub relationship
    """
    result, indexes = get_dict("relationships")

    channels = get_topics()
    count = 1
    for channel in channels:
        sub_names = get_sub_list(channel)
        for sub_name in sub_names:
            result['data'].append({"key": count, indexes[0]: channel, indexes[1]: sub_name})
            count = count + 1

    return jsonify(result)


@app.route('/subscriber', methods=["GET"])
def get_all_host_info():
    """Get all the subscriber's information
    """
    result, indexes = get_dict("subscriber")

    host_names = get_hosts()
    count = 1
    for host_name in host_names:
        host_info = get_host_info(host_name)
        item = {"key": count}
        for index in indexes:
            if index in host_info:
                item[index] = host_info[index]
            else:
                item[index] = host_name
        result['data'].append(item)
        count = count + 1

    return jsonify(result)


@app.route('/publisher', methods=["GET"])
def get_all_topic_info():
    """Get the topic host information
    """
    result, indexes = get_dict("publisher")

    topic_names = get_topics()
    count = 1
    for topic_name in topic_names:
        topic_info = get_topic_info(topic_name)
        item = {"key": count}
        for index in indexes:
            if index in topic_info:
                item[index] = topic_info[index]
            else:
                item[index] = topic_name
        result['data'].append(item)
        count = count + 1
    return jsonify(result)


def get_topo_nodes(key: Dict):
    """Get the topo nodes according to the
    keys

    Args:
        key: The key list
    """
    nodes = get_topo_nodes_fromdb()
    result = []
    node_type = {}
    for node in nodes:
        item = {}
        if type(node) == int:
            item[key[1]] = "switch"
            item[key[0]] = "s" + str(node)
        else:
            item[key[1]] = "host"
            item[key[0]] = node

        # The position is not defined
        item[key[2]] = randint(100, 501)
        item[key[3]] = randint(100, 501)
        result.append(item)
        node_type[node] = item[key[1]]
    return result, node_type


def get_edge_label(bandwidth, delay):
    """Get the label on an edge

    Args:
        bandwidth: The bandwidth of the edge
        delay: The delay of the edge
    """
    return str(delay) + "ms," + str(bandwidth) + "Mbit/s"


def get_topo_edges(key: Dict, node_type: Dict):
    """Get the topo edges according to the
    key

    Args:
        key: The key list
        node_type: Get the node type by name
    """
    edges = get_topo_edges_total_info_fromdb()
    nondp_edges = set()
    for edge in edges:
        label = get_edge_label(edge["bandwidth"], edge["delay"])
        src, dst = sorted([edge["src"], edge["dst"]])

        nondp_edges.add((src, dst, label))

    result = []
    for edge in nondp_edges:
        item = {}
        for index, value in enumerate(edge):
            item[key[index]] = value
        result.append(item)

    return result


@app.route('/topo', methods=["GET"])
def get_topo_info():
    ref_yaml = read_yaml(CONFIG_PATH)['topo']
    nodes, node_type = get_topo_nodes(ref_yaml["nodes"])
    edges = get_topo_edges(ref_yaml["edges"], node_type)
    result = {"nodes": nodes, "edges": edges}
    return result


if __name__ == '__main__':
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)
