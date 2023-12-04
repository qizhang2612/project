#!/usr/bin/env python3
import socket
import json
import asyncio
import aiohttp

from lib.py.net.util import get_socket
from lib.py.json.json import get_json
from lib.py.json.json import print_json


MAX_BUF_LEN = 512
CONTROLLER_PORT = 8888
DATA_PORT = 8889
DATA_IP = '127.0.0.1'
CONFIG_FILE_PATH = './main/pub_sub/host/conf/info/host_info.json'
IP_FILE_PATH = './main/pub_sub/host/conf/info/ip.json'
SERVER_INFO_FILE_PATH = './main/pub_sub/host/conf/info/server_info.json'
SYNC_PORT = 2323
RAND_PORT = 5555
SYNC_TO_PORT = 7373
HIS_FILE_PATH = '/history'
SENDER_FILE_PATH = '/sender'


def parse_cmd(input_str: str) -> tuple:
    """To parse the user's input string

    Args:
        input_str: The user's input string

    Returns:
        A tuple which contains:
        1. whether the user input a right command
        2. the command's type
        3. the command's extra parameter
    """
    input_list = input_str.split(' ')
    command_type = ''
    command_argv = ''

    for item in input_list:
        if item == '':
            continue
        elif command_type == '':
            command_type = item
        elif command_argv == '':
            command_argv = item
        else:
            break

    if command_type == 'pub' or command_type == 'reg' or command_type == 'pull' \
            or command_type == 'unpub' or command_type == 'getrc':
        return 1, command_type, ''
    elif command_type == 'sub' or command_type == 'unsub' or command_type == 'geth':
        return 1, command_type, command_argv
    else:
        return 0, 'failed', ''


async def solve_input(server_ip: str, server_port: int, host_ip: str,
                      command_type: str, command_argv: str):
    """Deal with the user's command

    Args:
        server_ip: The ip address of the server
        server_port: The port of the server
        host_ip: The ip address of the host
        command_type: Command's type
        command_argv: The command's extra parameter

    Returns:
        1. Whether the command executed successfully or not
        2. The reply packet of the controller
    """
    # the command don't need send message to the controller
    if command_type == 'geth' or command_type == 'getrc':
        return 1, ''

    if command_argv != '':
        ret_msg = command_argv
    else:
        ret_msg = ''

    # If the command is pub, reg or unpub, all the host's information
    # should be appended to the querying message.
    if command_type == 'pub' or command_type == 'reg' or command_type == 'unpub':
        json_file_config = get_json(CONFIG_FILE_PATH)
        need_keys = ['name', 'type', 'location', 'description']
        for key in need_keys:
            if key not in json_file_config:
                return 0, ''
        ret_msg = json.dumps(json_file_config)

    if command_type == 'unpub':
        # we make the controller to finish the synchronizing work
        pass
    # now we should add the bandwidth and delay demand

    if command_type == 'sub':
        json_file_config = get_json(CONFIG_FILE_PATH)
        need_keys = ['bandwidth', 'delay']
        send_json = {'topic': command_argv}
        for key in need_keys:
            if key not in json_file_config:
                return 0, ''
            send_json[key] = json_file_config[key]
        ret_msg = json.dumps(send_json)
    print(ret_msg)
    async with aiohttp.ClientSession("http://" + server_ip + ":" + str(server_port)) as session:
        body = {
            "command": command_type,
            "info": ret_msg,
            "host_ip": host_ip
        }
        async with session.post('/pub_sub', json=body) as resp:
            if resp.status == 200:
                ret_msg = await resp.text()
                return 1, ret_msg

    ret_msg = {"msg": "There are something wrong with the remote web server",
               "status": "Failed"}
    return 0, json.dumps(ret_msg)


async def solve_history(db_ip, db_port, command_str: str, help_str: str = ''):
    """Solve the getrc and geth command

    Args:
        sk_mysql: the socket connected to the local database
        command_str: the value should be 'getrc' or
                    'geth+{someone in getrc's list}',which means the command type
        help_str: the str which will be print to note the user which command has finished.
        db_ip: The database ip address
        db_port: The database service's port
    """
    async with aiohttp.ClientSession('http://' + db_ip + ':' + str(db_port)) as session:
        body = {
            "info": command_str
        }
        async with session.post('/database', json=body) as resp:
            result_status = resp.status
            result_str = await resp.text()

    if result_status == 200:
        if result_str[-1] == '$':
            result_str = result_str[:len(result_str) - 1]
        result_dict = json.loads(result_str)
        print(help_str)
        for index, channel in enumerate(result_dict['msg']):
            print(str(index) + '.: ' + channel)
    else:
        print("status code: " + str(result_status) +
              "inner_message: There is something wrong with database")


async def solve_result(ret_msg: str, command_type: str, command_argv: str,
                       db_ip=DATA_IP, db_port=DATA_PORT):
    """Deal with the controller's reply packet

    Args:
        ret_msg: The controller's reply packet
        command_type: The command's type
        command_argv: The command's extra parameter
        db_ip: The local database ip address
        db_port: The local database ip port
    """
    # Now we use the Flask, and http protocol
    # if command_type not in ['pull', 'reg']:
    #     sk_mysql = get_socket(address='127.0.0.1', port=4321,
    #                           connect_type=socket.SOCK_STREAM,
    #                           connect_ip='127.0.0.1', connect_port=DATA_PORT)

    if command_type not in ['geth', 'getrc']:
        data = json.loads(ret_msg)
        print_json(data)
        if 'status' not in data or data['status'] == 'failed':
            return
    else:
        if command_type == 'getrc':
            await solve_history(db_ip, db_port,
                                command_type, "The received channel(s):  ")
        else:
            await solve_history(db_ip, db_port,
                                command_type + ' ' + command_argv,
                                "channel %s has sent message:" % command_argv)
        return

    # To solve the pub and unpublished command's reply,
    # I construct the querying string and send it to
    # the local database
    ret = ''
    if command_type == 'pub' or command_type == 'unpub':
        if command_type == 'pub':
            ret = 'pub ' + data['group_addr'] + \
                  ' ' + data['location'] + ' ' + data['topic_name']
        else:
            ret = 'unpub ' + get_json(IP_FILE_PATH)['ip'] + \
                  ' ' + data['location'] + ' ' + data['topic_name']

    # To solve the subscribing and unsubscribing command's reply,
    # I construct the querying string and send it to
    # the local database
    if command_type == 'sub' or command_type == 'unsub':
        if command_type == 'sub':
            ret = 'sub ' + data['pub_ipv4'] + \
                  ' ' + data['location'] + ' ' + data['topic_name']
        else:
            ret = 'unsub ' + data['pub_ipv4'] + \
                  ' ' + data['location'] + ' ' + data['topic_name']

    # send the ret to the database
    if ret:
        async with aiohttp.ClientSession(
                'http://' + DATA_IP + ":" + str(DATA_PORT)) as session:

            body = {
                "info": ret
            }
            async with session.post('/database', json=body) as resp:
                result_status = resp.status
                result_str = await resp.text()
                if result_status == 200:
                    print(result_str)
                else:
                    print("status code: " + str(result_status) +
                          "inner_message: There is something wrong with the database")


async def user_interface():
    """User interface
    """
    global DATA_IP
    host_ip = get_json(IP_FILE_PATH)['ip']
    DATA_IP = host_ip
    json_server_info = get_json(SERVER_INFO_FILE_PATH)
    server_ip = json_server_info['server_ip']
    server_port = json_server_info['server_port']
    step = 1
    while True:
        step = 0
        user_input = input('pub_sub>>').strip()

        res, user_type, user_argv = parse_cmd(user_input)
        if res == 0:
            continue
        statue, msg = await solve_input(server_ip, server_port, host_ip,
                                        user_type, user_argv)

        await solve_result(msg, user_type, user_argv,
                           DATA_IP, DATA_PORT)
    return 0


if __name__ == '__main__':
    # json_file_ip = get_json(IP_FILE_PATH)
    #
    # socket_recv = get_socket(address=json_file_ip['ip'],
    #                          port=CONTROLLER_PORT,
    #                          connect_type=socket.SOCK_DGRAM)
    # socket_send = get_socket(address=IP,
    #                          port=CONTROLLER_PORT,
    #                          connect_type=socket.SOCK_DGRAM)
    #
    # # the step is used to debug
    # step = 1
    # while True:
    #     step = 0
    #     user_input = input('pub_sub>>').strip()
    #
    #     res, user_type, user_argv = parse_cmd(user_input)
    #     if res == 0:
    #         continue
    #     statue, msg = solve_input(socket_send,
    #                               socket_recv,
    #                               user_type, user_argv)
    #     print(msg)
    #     if statue == 1:
    #         solve_result(msg, user_type, user_argv)
    asyncio.run(user_interface())


