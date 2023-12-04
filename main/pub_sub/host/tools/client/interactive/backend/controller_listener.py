#!/usr/bin/env python3
import socket

from lib.py.net.util import get_socket
from lib.py.json.json import get_json

PORT = 2323
DB_PORT = 8889
MAX_BUF_SIZE = 512

CONFIG_FILE_PATH = './main/pub_sub/host/conf/info/host_info.json'
IP_FILE_PATH = './main/pub_sub/host/conf/info/ip.json'


def solve(ret_msg: str):
    """Use the topic's information to delete
    the deleting topic

    Args:
        ret_msg: A dict representing the topic's information

    Returns:
          If we have done the synchronizing successfully, we will get "{'status': 'success'}". And
          if not, we will get '{"status": "failed", "msg": "wrong cmd sync"}' back
    """
    arrmsg = ret_msg.split(' ')
    if arrmsg[0] != 'sync':
        return -1

    sk_mysql = get_socket(address='127.0.0.1', port=PORT,
                          connect_type=socket.SOCK_STREAM,
                          connect_ip='127.0.0.1',
                          connect_port=DB_PORT)

    sk_mysql.send(ret_msg.encode('utf-8'))
    res = sk_mysql.recv(1024).decode('utf-8')
    sk_mysql.close()
    return res


if __name__ == '__main__':
    json_file = get_json(IP_FILE_PATH)
    # Open a port to listen the synchronizing request
    server = get_socket(address=json_file['ip'],
                        connect_type=socket.SOCK_DGRAM,
                        port=PORT)

    print('listen the %d port' % PORT)
    while True:
        msg = server.recvfrom(MAX_BUF_SIZE)[0]
        msg = msg.decode('utf-8')
        print(msg)
        solve(msg.strip())
