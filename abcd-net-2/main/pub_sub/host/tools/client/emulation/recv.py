#!/usr/bin/env python3
import socket
from time import sleep
from lib.py.net.util import get_socket
from lib.py.json.json import get_json


IP_PATH = './main/pub_sub/host/conf/info/ip.json'
RECV_PORT = 9000
RAND_PORT = 5353
DB_PORT = 8889


if __name__ == '__main__':
    ip = get_json(IP_PATH)['ip']
    sk = get_socket(address=ip, port=RECV_PORT,
                    connect_type=socket.SOCK_DGRAM)

    while True:
        sk_mysql = get_socket(address='127.0.0.1',
                              connect_type=socket.SOCK_STREAM,
                              port=RAND_PORT,
                              connect_ip='127.0.0.1',
                              connect_port=DB_PORT)

        res = sk.recvfrom(1024)[0]
        msg = 'rech ' + res.decode('utf-8')
        print('recv: ', res.decode('utf-8'))
        sleep(1)
        sk_mysql.send(msg.encode('utf-8'))
        res = sk_mysql.recv(1024)
        sk_mysql.close()

