import socket
import asyncio


class NonBlockSocket(object):
    def __init__(self, bind_ip: str = "", bind_port: int = 0,
                 connect_type=None, connect_ip: str = "", connect_port: int = 0):
        self.sk = None
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.connect_type = connect_type
        self.connect_ip = connect_ip
        self.connect_port = connect_port
        self.build_socket()

    def udp_recv(self, size: int = 1024):
        """Encapsulate the recvfrom method of socket

        Args:
            size: The buffer size
        """
        try:
            data, address = self.sk.recvfrom(1024)
        except Exception as ez:
            # give up running
            await asyncio.sleep(0)
            return None, None
        return data.decode('utf-8'), address

    def udp_send(self, message, address):
        """Encapsulate the sendto method of socket

        Args:
            message: The message wanted to send
            address: The address wanted to received
        """
        self.sk.sendto(message, address)

    def build_socket(self):
        """Now the non_block_socket only support the udp
        """
        self.sk = socket.socket(family=socket.AF_INET,
                                type=self.connect_type,
                                proto=0)
        self.sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sk.setblocking(False)
        self.sk.bind(self.bind_ip, self.bind_port)
