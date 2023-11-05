from flask import Flask
from flask import jsonify
from flask_cors import CORS
from pub_sub.dir_server.lib.dir_view import get_topics
from pub_sub.dir_server.lib.dir_view import get_sub_list
from pub_sub.dir_server.lib.dir_view import get_topic_info
from pub_sub.dir_server.lib.dir_view import get_hosts
from pub_sub.dir_server.lib.dir_view import get_host_info

app = Flask(__name__)
cors = CORS(app)


@app.route('/v1/topics')
def get_topic_names():
    channels = get_topics()
    ret = {
        "msg": channels,
        "status": 200
    }

    return jsonify(ret)


@app.route('/v1/relations')
def get_pub_sub_relations():
    """
    Returns:
    example:
        {
          "msg": [
            {
              "description": "this is a w",
              "ip": "10.0.0.1",
              "location": "area A",
              "sub": [
                "20.0.0.3",
                "20.0.0.2",
                "20.0.0.1"
              ],
              "topic": "w1",
              "type": "w"
            }，
            ...
          ],
          "status": 200
        }
    """
    pub_subs = []
    channels = get_topics()

    for channel in channels:
        subscribers = get_sub_list(channel)
        topic_info = get_topic_info(channel)
        item = generate_relation_item(channel, topic_info, subscribers)
        pub_subs.append(item)

    ret = {
        "msg": pub_subs,
        "status": 200
    }
    return jsonify(ret)


@app.route('/v1/hosts')
def get_all_host_info():
    hosts = []
    host_names = get_hosts()
    for host in host_names:
        host_info = get_host_info(host)
        item = generate_host_item(host, host_info)
        hosts.append(item)

    ret = {
        "msg": hosts,
        "status": 200
    }
    return jsonify(ret)


def generate_relation_item(channel, topic_info, subscribers):
    item = dict()

    item['topic'] = channel
    item['sub'] = subscribers
    item['type'] = topic_info['type']
    item['location'] = topic_info['location']
    item['description'] = topic_info['description']
    item['ip'] = topic_info['ip']

    return item


def generate_host_item(host, host_info):
    item = dict()

    item['host_name'] = host
    item['type'] = host_info['type']
    item['location'] = host_info['location']
    item['description'] = host_info['description']
    item['ip'] = host_info['ip']
    return item


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=33333)
