import socket
import aiohttp
import sys

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


async def get_address(ret_msg: str, local_port: int, db_port: int,
                      db_address: str = '127.0.0.1') -> str:
    """Get topic's or subscriber's IP address

    Args:
        ret_msg: The query sentence to query IP address from local database
        local_port: A random port to connect the database
        db_port: The database's port
        db_address: The database's address
    """
    async with aiohttp.ClientSession("http://" + db_address + ":" + str(db_port)) as session:
        body = {
            "info": ret_msg
        }
        async with session.post('/database', json=body) as reps:
            result_status = reps.status
            if result_status == 200:
                result_str = await reps.text()
                return get_msg(result_str)
            else:
                print('status code: ' + str(result_status) +
                      " message: There is something wrong with database")
                sys.exit(-1)

    return get_msg(ret_msg.decode('utf-8'))
