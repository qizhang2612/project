import socket
import logging
import json

from main.dir_server.view.host_view import record_pub_info
from main.dir_server.view.host_view import record_sub_info
from main.dir_server.view.host_view import get_pub_address
from main.dir_server.view.host_view import get_sub_info
from main.dir_server.view.host_view import delete_sub_info
from main.dir_server.view.host_view import delete_pub_info
from main.dir_server.view.host_view import record_history_msg
from main.dir_server.view.host_view import get_channel_history
from main.dir_server.view.host_view import get_recv_channel
from main.dir_server.view.host_view import record_recv_channel
from lib.py.json.json import check_keys


HOST = '127.0.0.1'
PORT = 8889
MAX_BUF_SIZE = 512
HIS_FILE_PATH = '/history'
SENDER_FILE_PATH = '/sender'


def execute_cmd(cmd):
    """Execute the command received from the pub_sub.py

    Args:
        cmd: the command string
    """
    result = None
    argv = parse_cmd(cmd)

    # If the command's parsing fails, we just return the failed
    # message
    if not argv:
        result = {"status": "failed", "msg": "wrong cmd " + cmd}
        return json.dumps(result)

    if argv[0] == "pub":  # solve the publishing request
        group_address, location, topic_name = argv[1], argv[2], argv[3]
        record_pub_info(group_address, location, topic_name)
        result = {"status": "success"}
    elif argv[0] == "sub":  # solve the subscribing request
        ipv4_address, location, topic_name = argv[1], argv[2], argv[3]
        record_sub_info(ipv4_address, location, topic_name)
        result = {"status": "success"}
    elif argv[0] == "get":  # solve the querying sub/pub information request
        address_type = argv[1]
        ret_info = get_pub_address() \
            if address_type == "pub" else get_sub_info()
        result = {"status": "success", "msg": ret_info}
    elif argv[0] == 'unsub':  # solve the unsubscribing request
        ipv4_address, location, topic_name = argv[1], argv[2], argv[3]
        delete_sub_info(ipv4_address, location, topic_name)
        result = {"status": "success"}
    elif argv[0] == 'unpub':  # solve the deleting topic request
        ipv4_address, location, topic_name = argv[1], argv[2], argv[3]
        delete_pub_info(ipv4_address, location, topic_name)
        result = {'status': 'success'}
    # When dealing the deleting topic request,
    # we should inform the subscribers to unsubscribe
    # the topic
    elif argv[0] == 'sync':
        ipv4_address, location, topic_name = argv[1], argv[2], argv[3]
        delete_sub_info(ipv4_address, location, topic_name)
        result = {'status': 'success'}
    # When receiving message,
    # we should record the topic's name,
    # which send the message.
    elif argv[0] == 'rech':
        json_dict = json.loads(argv[1])
        if check_keys(json_dict, ["channel", "msg"]):
            record_history_msg((json_dict['channel'], json_dict['msg']))
            result = {'status': 'success'}
            sender_list = get_recv_channel()
            if json_dict['channel'] not in sender_list:
                record_recv_channel(json_dict['channel'])
        else:
            result = {"status": "failed",
                      "msg": "wrong format of history message"}
    # Solve the querying history message request.
    elif argv[0] == 'geth':
        res = get_channel_history(argv[1])
        result = {"status": "success", "msg": res}
        end_result = json.dumps(result)
        end_result = end_result + '$'
        return end_result
    # Solve the querying topics' name request, from which
    # we received message
    elif argv[0] == 'getrc':
        res = get_recv_channel()
        result = {"status": "success", "msg": res}
        end_result = json.dumps(result)
        end_result = end_result + '$'
        return end_result
    else:
        pass

    return json.dumps(result)


def parse_cmd(cmd):
    """Parse the querying message

    Args:
        cmd: the querying message, which
        is formatted as " 'command type' + 'extra parameters' "
    """
    argv = cmd.strip().split(' ')
    if len(argv) and argv[0] in ["pub", "sub", "get",
                                 "unsub", "unpub", "sync",
                                 "rech", "geth", "getrc"]:
        if argv[0] != "rech":
            return argv
        else:
            return [argv[0], cmd[len(argv[0]):]]
    else:
        return []


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s:%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    while True:
        logging.info("listening for storage request...")
        client_socket, _ = server.accept()

        msg = client_socket.recv(MAX_BUF_SIZE)
        msg_data = msg.decode("utf-8")
        logging.info("receive msg: " + msg_data)

        reply = execute_cmd(msg_data)

        if reply:
            client_socket.send(reply.encode("utf-8"))
            logging.info("reply msg: " + str(reply))
        else:
            pass

        client_socket.close()
