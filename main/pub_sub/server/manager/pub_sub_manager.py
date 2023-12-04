import logging
import json
from time import sleep
import socket
from typing import Dict
import aiohttp

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import udp
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto

from main.dir_server.view.server_view import get_topics
from main.dir_server.view.server_view import get_groups
from main.dir_server.view.server_view import publish_new_topic
from main.dir_server.view.server_view import delete_topic

from main.dir_server.view.server_view import get_topic_info
from main.dir_server.view.server_view import get_sub_list
from main.dir_server.view.server_view import subscribe_topic
from main.dir_server.view.server_view import unsubscribe_topic
from main.dir_server.view.server_view import register_host
from main.dir_server.view.server_view import get_hosts
from main.dir_server.view.server_view import find_host_name_by_ip
from main.dir_server.view.server_view import get_host_info
from lib.py.net.util import get_socket

IP = '10.0.0.100'  # For sync
SYNC_FROM_PORT = 7373
HOST_DATA_PORT = 8889
SYNC_TO_PORT = 2323
CONTROLLER_IP = '10.0.0.100'


class PubSubManager(object):
    """Deal with pub sub request cmd.

-- reset master;

show binary logs;
    Attributes:
        cmd_type: A string indicate the cmd type.
        optional values: "pull", "pub", "sub", "reg".
        source_ip: A string of ip of cmd sender.
        group_ip: A string of ip of corresponding group address.
        results: A dict of results of command execution.
        update: A boolean indicate whether this cmd
                impact the pub sub membership.
        msg2tm: If the operation is pub, sub, unpub or unsub , the msg2tm
        will be not empty and trafficmanager use the it update the topology
    """

    def __init__(self):
        self.cmd_type = None
        self.source_ip = None
        self.group_ip = None

        self.results = {}
        self.update = False

        self.msg2tm = {}

    async def pub_sub_handler(self, cmd, ip=None):
        """Distribute pub sub request.

        Parse cmd type and distribute it to
        corresponding function.

        Args:
            cmd: A string of cmd to be dealt with.
            ip:  A ipv4 instance of cmd sender.
        """
        # self.source_ip = ip.src if ip else None
        self.source_ip = cmd['host_ip']

        argv = self._translate_cmd(cmd)
        logging.info("process cmd [" + json.dumps(cmd) + "] from " + self.source_ip)

        if argv[0] == 'pub':  # publish the topic
            self._pub_channel(argv, group_addr=self.msg2tm['group_ip'])
            self.cmd_type = 'pub'
        elif argv[0] == 'sub':  # subscribe some topics
            self._sub_channel(argv, channel=self.msg2tm['topic_name'],
                              host_name=self.msg2tm['host_name'])
            self.cmd_type = 'sub'
        elif argv[0] == 'pull':  # get information
            self._pull_channels()
            self.cmd_type = 'pull'
        elif argv[0] == 'reg':  # register, before subscribing some topics
            self._register_host(argv)
            self.cmd_type = 'reg'
        elif argv[0] == 'unsub':  # unsubscribe the topic
            self._unsubscribe(argv[1])
            self.cmd_type = 'unsub'
        elif argv[0] == 'unpub':  # cancel the topic
            await self._delete_topic(argv)
        else:
            self.cmd_type = 'wrong'
            self.results = {"status": "failed", "msg": "wrong cmd syntax."}

    @staticmethod
    def _cmd_parser(cmd):
        """Split cmd into elements.

        Args:
            cmd: A string of pub-sub app cmd.
        """
        stripped_cmd = cmd.strip()
        argv = stripped_cmd.split()
        if argv[0] == 'pub' or argv[0] == 'reg' or argv[0] == 'unpub' \
                or argv[0] == 'sub':
            json_argv = list()
            json_argv.append(argv[0])
            json_argv.append(stripped_cmd[len(argv[0]):].strip())
            return json_argv

        return argv

    def check_pub(self, argv):
        """Check the pub operation is available or not

        Args:
            argv: The information of the pub operation
        """
        pass
        data = get_topics(strong_consistent=True)

        pub_info = json.loads(argv[1])

        channel = pub_info["name"]
        if channel in data:
            # topic name used.
            msg = "Topic " + channel + " used, must pick another one."
            logging.warning(msg)
            self.results = {"status": "failed", "msg": msg}
            return False
        group_id = self.get_available_group_id()
        topic_info = {"topic_name": pub_info["name"],
                      "ip": self.source_ip,
                      "group_addr": group_id}
        self.build_msg2tm(op='pub', topic_info=topic_info,
                          src_ip=self.source_ip)
        return True

    def check_sub(self, argv):
        """Check the sub operation is available or not

        Args:
            argv: The information of the pub operation
        """
        sub_info = json.loads(argv[1])
        channel = sub_info['topic']
        data = get_topics()
        if channel in data:
            host_name = find_host_name_by_ip(self.source_ip)
            if not host_name:
                msg = "Host " + host_name + " not register, must register first."
                logging.warning(msg)
                self.results = {"status": "failed", "msg": msg}
                return False
            subscribers = get_sub_list(channel)
            if host_name not in subscribers:
                topic_info = get_topic_info(channel)
                topic_info['topic_name'] = channel
                self.build_msg2tm(op='sub', topic_info=topic_info,
                                  src_ip=self.source_ip,
                                  bandwidth=sub_info['bandwidth'],
                                  delay=sub_info['delay'],
                                  host_name=host_name)
                return True
            else:
                msg = "Topic " + channel + " already subscribed by " + host_name + ":" + self.source_ip
                logging.warning(msg)
                self.results = {"status": "failed", "msg": msg}
                return False
        else:
            msg = "Topic " + channel + " not found, check topic name again."
            logging.error(msg)
            self.results = {"status": "failed", "msg": msg}
        return False

    def check_unsub(self, channel):
        """Check the unsub operation is legal or not
        in pub_sub system.

        Args:
            channel: The name of the topic wanted to be unsubscribed
        """
        data = get_topics()
        if channel in data:
            host_name = find_host_name_by_ip(self.source_ip)
            if not host_name:
                msg = "Host " + host_name + " not register, must register first."
                logging.warning(msg)
                self.results = {"status": "failed", "msg": msg}
                return False

            subscribers = get_sub_list(channel)
            if host_name in subscribers:
                # unsubscribe_topic(channel, host_name)
                topic_info = get_topic_info(channel)
                topic_info['topic_name'] = channel
                self.build_msg2tm(op='unsub', topic_info=topic_info,
                                  src_ip=self.source_ip, host_name=host_name)
                return True
            else:
                msg = "Topic " + channel + " have not subscribed by " + host_name + ":" + self.source_ip
                logging.warning(msg)
                self.results = {"status": "failed", "msg": msg}
                return False
        else:
            msg = "Topic " + channel + " not found, check topic name again."
            logging.error(msg)
            self.results = {"status": "failed", "msg": msg}
            return False

    def check_unpub(self, argv):
        """Check the unpub operation is legal or not
        in pub_sub system.

        Args:
            argv: The parameters of the topic who want to unpub
        """
        data = get_topics(strong_consistent=True)
        pub_info = json.loads(argv[1])
        channel = pub_info["name"]
        location = pub_info["location"]
        if channel not in data:
            msg = "Topic " + channel + " has not published, please publish first"
            logging.warning(msg)
            self.results = {"status": "failed", "msg": msg}
            return False
        else:
            topic_info = get_topic_info(channel)
            # self.delete_members(channel, topic_info)
            # delete_topic(channel)
            topic_info['topic_name'] = channel
            self.build_msg2tm(op='unpub', topic_info=topic_info,
                              src_ip=self.source_ip)
            return True

    def _pub_channel(self, argv, group_addr: str = ''):
        """publish channel from user request.

        Data operations are strongly consistent ——
        directly load from db.

        There is one single thread running in
        each RYU application, so there is no need to
        consider multi-thread condition.

        Args:
            argv: A list a pub cmd elements.
        """
        # data = get_topics(strong_consistent=True)
        #
        # pub_info = json.loads(argv[1])
        #
        # channel = pub_info["name"]
        # channel_type = pub_info["type"]
        # location = pub_info["location"]
        # description = pub_info["description"]
        #
        # if channel in data:
        #     # topic name used.
        #     msg = "Topic " + channel + " used, must pick another one."
        #     logging.warning(msg)
        #     self.results = {"status": "failed", "msg": msg}
        #     return
        # else:
        #     if not group_addr:
        #         group_id = self.get_available_group_id()
        #     else:
        #         group_id = group_addr
        #
        #     publish_new_topic((channel, channel_type, location,
        #                        description, self.source_ip, group_id))

        # waiting for db sync. Avoid the same id generated.
        pub_info = json.loads(argv[1])

        channel = pub_info["name"]
        channel_type = pub_info["type"]
        location = pub_info["location"]
        description = pub_info["description"]

        if not group_addr:
            group_id = self.get_available_group_id()
        else:
            group_id = group_addr

        publish_new_topic((channel, channel_type, location,
                           description, self.source_ip, group_id))
        syn = 0
        for _ in range(10):
            data = get_topics(strong_consistent=True)
            if channel in data:

                syn = 1
                msg = "Publish topic success."
                self.results = {"status": "success", "msg": msg,
                                "group_addr": group_id, "location": location,
                                "topic_name": channel}
                break

            logging.warning("retying for fetching published topic from database.")
            sleep(0.1)

        if not syn:
            msg = "Topic " + channel + " write failed - can not write into db."
            logging.error(msg)
            self.results = {"status": "failed", "msg": msg}

    def _sub_channel(self, argv, channel, host_name):
        """Deal with sub request from host.

        Args:
            argv: A list of sub cmd elements.
            channel: The name of the topic wanted to be subscribed
            host_name: The name of the subscriber
        """
        subscribe_topic(channel, host_name)
        topic_info = get_topic_info(channel)
        msg = "Topic " + channel + " subscribed by " + host_name + ":" + self.source_ip
        logging.info(msg)
        self.results = {"status": "success", "msg": msg,
                        "pub_ipv4": topic_info['ip'],
                        "location": topic_info['location'],
                        "topic_name": channel}

    def _pull_channels(self):
        """Deal with pull channel request.

        Returns: A list of all topic info.
            example:
            [
                {'name': 'w1', 'type': 'w', 'location': 'area B',
                 'description': 'this is a w', 'ip': '10.0.0.2',
                 'group_addr': '232.0.0.2', 'name': 'w2'},
                 {'name': 'w2', 'type': 'w', 'location': 'area A',
                'description': 'this is a w', 'ip': '10.0.0.1',
                'group_addr': '232.0.0.1', 'name': 'w1'}
            ]
        """
        data = get_topics()
        msg = []
        for topic in data:
            topic_info = get_topic_info(topic)
            topic_info['name'] = topic
            msg.append(topic_info)
        self.results = {"status": "success", "msg": msg}

    def _register_host(self, argv):
        """The subscriber should register its own information
            to the controller

        Args:
            argv: A dict contains the host's all information,
                which it want to tell the controller
        """
        reg_info = json.loads(argv[1])

        host_name = reg_info["name"]
        host_type = reg_info["type"]
        location = reg_info["location"]
        description = reg_info["description"]

        hosts = get_hosts()
        if host_name in hosts:
            # the host has registered
            msg = "Host name " + host_name + " used. must pick another one."
            logging.warning(msg)
            self.results = {"status": "failed", "msg": msg}
            return
        # save the information into the database
        register_host((host_name, host_type, location, description, self.source_ip))

        syn = 0
        for _ in range(10):
            data = get_hosts()
            if host_name in data:
                syn = 1
                msg = "register success."
                self.results = {"status": "success", "msg": msg}
                break
            logging.warning("retying for fetching registered host from database.")
            sleep(0.1)

        if not syn:
            msg = "Host " + host_name + " write failed - can not write into db."
            logging.error(msg)
            self.results = {"status": "failed", "msg": msg}

    def _unsubscribe(self, channel: str = ''):
        """Unsubscribe the topic

        Args:
            channel: the topic's name
        """
        host_name = self.msg2tm['host_name']
        unsubscribe_topic(channel, host_name)
        topic_info = get_topic_info(channel)
        msg = "Topic " + channel + " unsubscribed by " + host_name + ":" + self.source_ip
        logging.info(msg)
        self.results = {"status": "success", "msg": msg,
                        "pub_ipv4": topic_info['ip'],
                        "location": topic_info['location'],
                        "topic_name": channel}
        # self.update = True
        # there should be more steps to cancel the flows, but we don't write it now

    async def _delete_topic(self, argv: list):
        """Cancel the topic

        Args:
            argv: A dict consists all the information
                    about the topic, which is used to
                    delete the topic from database
        """
        pub_info = json.loads(argv[1])
        channel = pub_info["name"]
        location = pub_info["location"]

        topic_info = get_topic_info(channel)
        await self.delete_members(channel, topic_info)
        delete_topic(channel)

        msg = "Unpublish topic success."
        self.results = {"status": "success", "msg": msg,
                        "location": location,
                        "topic_name": channel
                        }

    async def delete_members(self, channel: str, topic_info: dict):
        """Delete the subscribers

        Args:
            channel: The topic name.
            topic_info: A dict contains the topic's information.
                        To synchronize the subscriber's database,
                        we need the topic's information
        """
        subscribers = get_sub_list(channel)
        for subscriber in subscribers:
            await self.sync_info(subscriber, channel, topic_info)
            if "status" in self.results \
                    and self.results["status"] == "Failed":
                return
            unsubscribe_topic(channel, subscriber)

    async def sync_info(self, subscriber: str,
                        channel: str, topic_info: dict):
        """To synchronize the subscriber's database

        Args:
            subscriber: the subscriber's name
            channel: the topic's name
            topic_info: A dict contains the topic's information.
                        To synchronize the subscriber's database,
                        we need the topic's information
        """
        sub_info = get_host_info(subscriber)
        msg = 'sync' + ' ' + topic_info['ip'] + ' ' + topic_info['location'] + ' ' + channel
        root_url = "http://" + sub_info['ip'] + ":" + str(HOST_DATA_PORT)
        async with aiohttp.ClientSession(root_url) as session:
            body = {
                "info": msg
            }
            async with session.post('/database', json=body) as resp:
                result_status = resp.status
                if result_status != 200:
                    self.results['status'] = 'Failed'
                    self.results['msg'] = await resp.text()

    @staticmethod
    def get_available_group_id():
        """Generate a available ip address for topic.

        Returns:
             A string of available ip address currently,
             None if there is no available ip address.
        """
        groups = get_groups()

        pre = '232.0.0.0'
        address_elements = pre.split(".")

        for pos in range(1, 4):
            start = 1 if pos != 1 else 2
            for address in range(start, 256):
                address_elements[-pos] = str(address)
                new_address = '.'.join(address_elements)
                if new_address not in groups:
                    return new_address

        return None

    def get_cmd_type(self):
        """provide attribute cmd_type.

        Returns:
            A string of current cmd type.
        """
        return self.cmd_type

    def updated(self):
        """provide attribute update.

        Returns:
            A string indicate whether this cmd
        bring changes for pub sub relationship.
        """
        return self.update

    @staticmethod
    def format_json(data):
        """To get a formatted json string

        Args:
            the json reference

        Returns:
            A formatted json string
        """
        json_formatted_str = json.dumps(data, indent=2)
        return json_formatted_str

    def build_reply(self, pkt):
        """Build the replay packet

        Args:
            pkt: The packet_in packet received by controller

        Returns:
            the constructed relay packet
        """
        eth = pkt.get_protocol(ethernet.ethernet)
        ip = pkt.get_protocol(ipv4.ipv4)
        udp_pkt = pkt.get_protocol(udp.udp)

        eth_head = ethernet.ethernet(dst=eth.src, src='00:0c:29:0e:42:45', ethertype=ether_types.ETH_TYPE_IP)
        ip_head = ipv4.ipv4(src=CONTROLLER_IP, dst=ip.src, proto=in_proto.IPPROTO_UDP)
        udp_head = udp.udp(dst_port=udp_pkt.dst_port)

        payload = json.dumps(self.results).encode('utf-8')
        print(self.results)

        reply_pkt = payload
        # reply_pkt = packet.Packet()
        # reply_pkt.add_protocol(eth_head)
        # reply_pkt.add_protocol(ip_head)
        # reply_pkt.add_protocol(udp_head)
        # reply_pkt.add_protocol(payload)
        # reply_pkt.serialize()
        return reply_pkt

    def build_msg2tm(self, op, topic_info: Dict, src_ip: str,
                     bandwidth=100, delay=0, host_name: str = ''):
        """Build the message send to traffic_manager

        Args:
            op: The operation's name, including pub, unpub, sub, unsub
            topic_info: A dict containing the message of topic
            src_ip: The ip address of the source
            bandwidth: The bandwidth demand of the flow
            delay: the delay demand of the flow
            host_name: The host's name
        """
        self.msg2tm['source_ip'] = topic_info['ip']
        self.msg2tm['group_ip'] = topic_info['group_addr']
        self.msg2tm['topic_name'] = topic_info['topic_name']
        if op == 'pub':
            self.msg2tm['op'] = 'create_tree'
        elif op == 'unpub':
            self.msg2tm['op'] = 'delete_tree'
        elif op == 'sub':
            self.msg2tm['op'] = 'add_leaf'
            self.msg2tm['leaf_ip'] = src_ip
            self.msg2tm['bandwidth'] = bandwidth
            self.msg2tm['delay'] = delay
            self.msg2tm['host_name'] = host_name
        elif op == 'unsub':
            self.msg2tm['op'] = 'delete_leaf'
            self.msg2tm['leaf_ip'] = src_ip
            self.msg2tm['host_name'] = host_name

    @staticmethod
    def _translate_cmd(msg_json):
        """Translate A json message into the message the origin pubSub manager uses.

        Args:
            msg_json: A json Dict message
        """
        argv = [msg_json['command'], msg_json['info']]
        return argv

    def check_cmd(self, cmd_str, ip=None):
        """First, check the cmd can be store into the database or not,
        then find the available path

        Args:
            cmd_str: The cmd_str
            ip: The packet's ip layer
        """
        # self.source_ip = ip.src if ip else None
        self.source_ip = cmd_str['host_ip']
        self.results = {}
        self.msg2tm = {}
        argv = self._translate_cmd(cmd_str)

        result = True
        if argv[0] == 'pub':
            result = self.check_pub(argv)
        elif argv[0] == 'sub':
            result = self.check_sub(argv)
        elif argv[0] == 'unsub':
            result = self.check_unsub(argv[1])
        elif argv[0] == 'unpub':
            result = self.check_unpub(argv)
        return result


