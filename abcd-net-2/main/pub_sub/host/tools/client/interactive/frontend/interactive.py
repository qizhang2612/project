#!/usr/bin/env python3
import socket
import json

from lib.py.net.util import get_socket
from lib.py.json.json import get_json
from lib.py.json.json import print_json

IP = "232.0.0.1"
MAX_BUF_LEN = 512
CONTROLLER_PORT = 8888
DATA_PORT = 8889
CONFIG_FILE_PATH = './main/pub_sub/host/conf/info/host_info.json'
IP_FILE_PATH = './main/pub_sub/host/conf/info/ip.json'
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


def solve_input(sk_send: socket, sk_recv: socket, command_type: str, command_argv: str):
    """Deal with the user's command

    Args:
        sk_send: The socket to send UDP to the controller
        sk_recv: The socket to receive controller's reply's packet
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
        ret_msg = command_type + ' ' + command_argv
    else:
        ret_msg = command_type

    # If the command is pub, reg or unpub, all the host's information
    # should be appended to the querying message.
    if command_type == 'pub' or command_type == 'reg' or command_type == 'unpub':
        json_file_config = get_json(CONFIG_FILE_PATH)
        need_keys = ['name', 'type', 'location', 'description']
        for key in need_keys:
            if key not in json_file_config:
                return 0, ''
        ret_msg = ret_msg + ' ' + json.dumps(json_file_config)

    if command_type == 'unpub':
        # we make the controller to finish the synchronizing work
        pass
    # now we should add the bandwidth and delay demand

    if command_type == 'sub':
        print('hello sub')
        json_file_config = get_json(CONFIG_FILE_PATH)
        need_keys = ['bandwidth', 'delay']
        send_json = {'topic': command_argv}
        for key in need_keys:
            if key not in json_file_config:
                return 0, ''
            send_json[key] = json_file_config[key]
        ret_msg = 'sub' + ' ' + json.dumps(send_json)
    print(ret_msg)
    sk_send.sendto(ret_msg.encode('utf-8'), (IP, CONTROLLER_PORT))
    ret_msg = sk_recv.recvfrom(1024)[0]
    return 1, ret_msg.decode('utf-8')


def solve_history(sk_mysql, command_type: str, help_str: str = ''):
    """Solve the getrc and geth command

    Args:
        sk_mysql: the socket connected to the local database
        command_type: the value should be 'getrc' or 'geth', which means the command type
        help_str: the str which will be print to note the user which command has finished.

    """
    sk_mysql.send(command_type.encode('utf-8'))
    ret = ''

    # If the result is so long that greater than
    # 1024, we will not be able to finish reading
    # it by only once socket.recv(1024). To solve
    # this problem, I appended a $ at the end of the
    # reply message. The reading should be stopped
    # until read a $
    while True:
        part = sk_mysql.recv(1024).decode('utf-8')
        ret = ret + part
        if part[-1] == '$':
            ret = ret[:len(ret) - 1]
            break

    result = json.loads(ret)
    print(help_str)
    for index, channel in enumerate(result['msg']):
        print(str(index) + '.: ' + channel)


def solve_result(ret_msg: str, command_type: str, command_argv: str):
    """Deal with the controller's reply packet

    Args:
        ret_msg: The controller's reply packet
        command_type: The command's type
        command_argv: The command's extra parameter
    """
    if command_type not in ['pull', 'reg']:
        sk_mysql = get_socket(address='127.0.0.1', port=4321,
                              connect_type=socket.SOCK_STREAM,
                              connect_ip='127.0.0.1', connect_port=DATA_PORT)

    if command_type not in ['geth', 'getrc']:
        data = json.loads(ret_msg)
        print_json(data)
        if 'status' not in data or data['status'] == 'failed':
            return
    else:
        if command_type == 'getrc':
            solve_history(sk_mysql, command_type, "The received channel(s):  ")
        else:
            solve_history(sk_mysql, command_type + ' ' + command_argv
                          , "channel %s has sent message:" % command_argv)
        sk_mysql.close()
        return

    # To solve the pub and unpublished command's reply,
    # I construct the querying string and send it to
    # the local database
    if command_type == 'pub' or command_type == 'unpub':
        if command_type == 'pub':
            ret = 'pub ' + data['group_addr'] + ' ' + data['location'] + ' ' + data['topic_name']
        else:
            ret = 'unpub ' + get_json(IP_FILE_PATH)['ip'] + ' ' + data['location'] + ' ' + data['topic_name']

        sk_mysql.send(ret.encode('utf-8'))

    # To solve the subscribing and unsubscribing command's reply,
    # I construct the querying string and send it to
    # the local database
    if command_type == 'sub' or command_type == 'unsub':
        if command_type == 'sub':
            ret = 'sub ' + data['pub_ipv4'] + ' ' + data['location'] + ' ' + data['topic_name']
            sk_mysql.send(ret.encode('utf-8'))
        else:
            ret = 'unsub ' + data['pub_ipv4'] + ' ' + data['location'] + ' ' + data['topic_name']
            sk_mysql.send(ret.encode('utf-8'))

    if command_type not in ['pull', 'reg']:
        sk_mysql.close()


if __name__ == '__main__':
    json_file_ip = get_json(IP_FILE_PATH)

    socket_recv = get_socket(address=json_file_ip['ip'],
                             port=CONTROLLER_PORT,
                             connect_type=socket.SOCK_DGRAM)
    socket_send = get_socket(address=IP,
                             port=CONTROLLER_PORT,
                             connect_type=socket.SOCK_DGRAM)

    # the step is used to debug
    step = 1
    while True:
        step = 0
        user_input = input('pub_sub>>').strip()

        res, user_type, user_argv = parse_cmd(user_input)
        if res == 0:
            continue
        statue, msg = solve_input(socket_send,
                                  socket_recv,
                                  user_type, user_argv)
        print(msg)
        if statue == 1:
            solve_result(msg, user_type, user_argv)


