from lib.py.net.util import get_socket
from lib.py.json.json import get_json
import socket


IP_FILE_PATH = "./main/pub_sub/host/conf/info/ip.json"


if __name__ == "__main__":
    fe = get_json(IP_FILE_PATH)
    ip = fe['ip']
    PORT = fe["found_port"]
    dst = fe["found_ip"]
    sk = get_socket(address=ip, port=PORT, connect_type=socket.SOCK_DGRAM)
    msg = "ANTS"
    sk.sendto(msg.encode("utf-8"), (dst, PORT))
