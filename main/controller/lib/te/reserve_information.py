# encoding: utf-8

from dataclasses import dataclass


@dataclass
class ReserveInformation:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    bandwidth: int
    priority: int


if __name__ == '__main__':
    test = ReserveInformation(src_ip='10.0.0.1', dst_ip='1111', src_port=1, dst_port=2, bandwidth=10, priority=1)
    print(test.dst_ip)