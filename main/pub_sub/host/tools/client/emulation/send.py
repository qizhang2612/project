#!/usr/bin/env python3
import json
import socket
import argparse
import time
import asyncio

from lib.py.net.util import get_socket
from lib.py.json.json import get_json
from lib.py.net.util import get_address


DATA_IP = ''
MAX_BUF_LEN = 512
MAX_ADDR_LEN = 50
DATA_PORT = 8889
RECV_PORT = 9000
RAND_PORT = 3333
CONFIG_FILE_PATH = './main/pub_sub/host/conf/info/host_info.json'
IP_FILE_PATH = './main/pub_sub/host/conf/info/ip.json'


def get_command_data() -> str:
    time.sleep(2)
    if int(time.time()) % 2 == 0:
        return '{\"area\": \"A\", \"location\": ' \
               '\"(longitude1, latitude1, altitude1)\"}'
    else:
        return '{\"area\": \"B\", \"location\": ' \
               '\"(longitude1, latitude1, altitude1)\"}'


def get_notification_data() -> str:
    time.sleep(2)
    if int(time.time()) % 2 == 0:
        return '{\"area\": \"A\", \"location\":' \
               ' \"(longitude1, latitude1, altitude1)\"}'
    else:
        return '{\"area\": \"B\", \"location\": ' \
               '\"(longitude1, latitude1, altitude1)\"}'


def get_user_data() -> str:
    result = input("msg>>")
    return result


def get_data(sim: bool, posi: bool) -> str:
    """Get the Random or use's data

    Args:
        sim: When the simulate is False, the user input the data,
                    which he wants to send, when the simulate is True,
                    we send the random data
        posi: When positive is False, the topic send message to
                    subscribers. When the positive is True, the
                    subscriber send messages to the topic
    """
    result = ''
    if sim:
        if posi:
            result = get_command_data()
        else:
            result = get_notification_data()
    else:
        result = get_user_data()

    return result


def send_data(msg: str, address: str) -> None:
    now_ip = get_json(IP_FILE_PATH)['ip']
    sk = get_socket(address=now_ip,
                    connect_type=socket.SOCK_DGRAM,
                    port=RAND_PORT,
                    connect_ip=address,
                    connect_port=RECV_PORT)
    sk.sendto(msg.encode('utf-8'), (address, RECV_PORT))
    sk.close()


async def solve_data(msg: str, pos: bool):
    if pos:
        addresses = await get_address('get sub', RECV_PORT, DATA_PORT,
                                      db_address=DATA_IP)
        for address in addresses:
            send_data(msg, address[0])
    else:
        address = await get_address('get pub', RECV_PORT, DATA_PORT,
                                    db_address=DATA_IP)
        send_data(msg, address)


def get_argv():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--simulate', action='store_true')
    parser.add_argument('-p', '--positive', action='store_true')
    args = parser.parse_args()
    return args


async def main():
    """The main function of the send for async loop
    """
    global DATA_IP
    DATA_IP = get_json(IP_FILE_PATH)['ip']
    args = get_argv()
    simulate = args.simulate
    positive = args.positive
    while True:
        res = get_data(simulate, positive)
        print(res)
        # make it a json like { "channel":"...", "msg":"..." }
        conf_json = get_json(CONFIG_FILE_PATH)
        send_res = {"channel": conf_json['name'], "msg": res}
        await solve_data(json.dumps(send_res), positive)


if __name__ == '__main__':
    asyncio.run(main())
