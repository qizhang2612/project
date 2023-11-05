import socket
from lib.py.json.json import get_msg

MAX_SOCKET_CONNECT_TIMES = 10


def get_socket(address: str, port: int,
               connect_type: str,
               connect_ip: str = '',
               connect_port: int = 0) -> socket:
    """create a socket

    To create a socket quickly, I write it into a function,
    If it is TCP, I will try MAX_LIMIT times to make it connected,
    and we just believe that the socket is sure to be connected

    Args:
        address: The local IP address you want to bind.
        port: The local port you want to bind.
        connect_type: If you want to get a TCP socket, just input socket.STREAM,
                        and if you want to get a UDP socket, just input socket.DREAM.
        connect_ip: This guy is meaningful only when the connect_type is socket.STREAM
                    and it means the TCP peer's IP address you want to connect.
        connect_port: This guy means the TCP peer's port you want to connect.

    Returns:
        The socket you want to build.
    """
    sk = socket.socket(family=socket.AF_INET,
                       type=connect_type,
                       proto=0)
    sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sk.bind((address, port))
    if connect_type == socket.SOCK_STREAM and connect_ip != '':
        res = 1
        left = MAX_SOCKET_CONNECT_TIMES
        while res != 0 and left != 0:
            res = sk.connect_ex((connect_ip, connect_port))
            left = left - 1
            left = 1  # Let's go unlimited times
        if res != 0:
            return None
    return sk


def get_address(ret_msg: str, local_port: int, db_port: int) -> str:
    """Get topic's or subscriber's IP address

    Args:
        ret_msg: The query sentence to query IP address from local database
        local_port: A random port to connect the database
        db_port: The database's port
    """
    sk = get_socket(address='127.0.0.1',
                    port=local_port,
                    connect_type=socket.SOCK_STREAM,
                    connect_ip='127.0.0.1',
                    connect_port=db_port)
    sk.send(ret_msg.encode('utf-8'))
    ret_msg = sk.recv(1024)
    sk.close()
    return get_msg(ret_msg.decode('utf-8'))
