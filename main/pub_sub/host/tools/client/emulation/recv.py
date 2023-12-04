#!/usr/bin/env python3
import socket
from time import sleep
from lib.py.net.util import get_socket
from lib.py.json.json import get_json
import asyncio
import aiohttp

IP_PATH = './main/pub_sub/host/conf/info/ip.json'
RECV_PORT = 9000
RAND_PORT = 5353
DB_PORT = 8889


async def keep_receiving():
    ip = get_json(IP_PATH)['ip']
    sk = get_socket(address=ip, port=RECV_PORT,
                    connect_type=socket.SOCK_DGRAM)
    while True:
        res = sk.recvfrom(1024)[0]
        msg = 'rech ' + res.decode('utf-8')
        print('recv: ', res.decode('utf-8'))
        sleep(1)
        async with aiohttp.ClientSession('http://' + ip + ":" + str(DB_PORT)) as session:
            body = {
                "info": msg
            }
            async with session.post('/database', json=body) as resp:
                result_status = resp.status
                result_str = await resp.text()
                if result_status != 200:
                    print('status code: ' + str(result_status) + "inner_message: " + result_str)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(keep_receiving())
