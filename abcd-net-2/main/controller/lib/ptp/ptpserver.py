import time
import subprocess
import os
import multiprocessing
import networkx
import copy
import socket 

from operator import attrgetter
from collections import defaultdict
from ryu.base import app_manager
from ryu.lib import hub
from ryu.app import simple_switch_13
from ryu.ofproto import ofproto_v1_3, ether, ofproto_v1_0, ofproto_v1_2
from ryu.lib.packet import ethernet, packet, ipv4, udp
from ryu.ofproto.inet import *
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from netstate.netstate_config import *

SOCKERPORT = 9999

class PTPClient:
    
    def __init__(self, server_addr,port,mode,portstr):
        self.port = port
        self.server_addr = server_addr
        self.mode = mode
        self.portstr = portstr
    
    def send(self):
        s = self.mode+self.portstr
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.server_addr, self.port))
        client.sendall(s.encode())
        while True:
            server_reply = client.recv(1024).decode()
            if(server_reply =="finish"):
                break
        client.close()

class PTPClockSync(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super().__init__(*_args, **_kwargs)
        self.name = app_ptp_clocksync_name
    
        # 依赖topology生成的网络拓扑
        self.app_topology = app_manager.lookup_service_brick(app_topology_name)

        self.dpid_level = {} #不同设备所处的层次
        #拓扑图获得的相关信息
        self.graph = networkx.graph.Graph()
        self.link_to_port = {}
        self.host_or_switch = {}
        self.switch_port_table = {}
        self.switch_ip_address = {}

        self.clocksync_thread = hub.spawn(self._ptp_clocksync)
    
    #初始化dpid相关信息
    def init_dpid_info(self):
        for dpid in self.graph.nodes:
            self.dpid_level[dpid] = 1024
    
    #更新dpid_level
    def update_dpid_level(self,dpid1,dpid2):
        self.dpid_level[dpid2] = self.dpid_level[dpid1] + 1

    #比较dpid_level
    def compare_dpid_level(self,dpid1,dpid2):
        if(self.dpid_level[dpid1] >= self.dpid_level[dpid2]):
            return True
        else:
            return False
    
    #得到dpid对应交换机的连接相关信息
    def get_dpidandport_info(self,dpid,port):
        s = []
        if(self.is_switch(dpid,port)):
            s.append(self.switch_ip_address[dpid][0])
            if(port == 1):
                s.append("enp1s0")
            elif(port == 2):
                s.append("enp2s0")
            elif(port == 3):
                s.append("enp3s0")
            elif(port == 4):
                s.append("enp4s0")
            elif(port == 5):
                s.append("enp5s0")
            elif(port == 6):
                s.append("enp6s0")
        else:
            s.append(self.switch_ip_address[dpid])
            s.append("enp1s0f0")
        self.logger.info(s)
        return s

    #得到相连的端口
    def get_neighbor_port(self,dpid,port):
        return self.link_to_port[(dpid,port)]
    

    #判断是交换机还是主机
    def is_switch(self,dpid,port):
        if(dpid == 2 or dpid == 3):
            return True
        else:
            return False

    #主时钟执行
    def master_process_exec(self,dpid,port):
        s = self.get_dpidandport_info(dpid,port)
        #self.logger.info(s)
        p = PTPClient(s[0],SOCKERPORT,"M",s[1])
        p.send()

    #从时钟执行
    def slave_process_exec(self,dpid,port):
        s = self.get_dpidandport_info(dpid,port)
        p = PTPClient(s[0],SOCKERPORT,"S",s[1])
        p.send()

    #入队，并与主时钟同步
    def ptp_append(self,queue, dpid, port):
        node = (dpid,port)
        queue.append(node)
        self.slave_process_exec(dpid,port)

    #出队，并作为作为主时钟同步
    def ptp_pop(self,queue):
        node = queue.pop(0)
        self.master_process_exec(node[0],node[1])
        self.logger.info(node)
        return node
    
    #graph:拓扑图，【dpid,port】:根节点，主时钟
    #由拓扑图构造生成树
    def ptp_tree(self,graph,dpid,port):
        queue = []
        node = (dpid,port)
        self.dpid_level[dpid] = 1
        queue.append(node)
        if(self.is_switch(dpid,port)):   
            for otherport in self.switch_port_table[dpid]:
                if(otherport != port):
                    othernode = (dpid,otherport)
                    queue.append(othernode)          
        while(len(queue)>0):
            nextnode=self.ptp_pop(queue) 
            neighbor=self.get_neighbor_port(nextnode[0],nextnode[1])
            if(self.compare_dpid_level(nextnode[0],neighbor[0]) != True):
                self.update_dpid_level(nextnode[0],neighbor[0])
                if(self.is_switch(neighbor[0],neighbor[1])):
                    self.ptp_append(queue,neighbor[0],neighbor[1])
                else:
                    self.slave_process_exec(neighbor[0],neighbor[1])

    #执行
    def _ptp_clocksync(self):
        hub.sleep(30)
        self.graph = copy.deepcopy(self.app_topology.graph)
        self.link_to_port = copy.deepcopy(self.app_topology.link_to_port)
        self.host_or_switch = copy.deepcopy(self.app_topology.host_or_switch)
        self.switch_port_table = copy.deepcopy(self.app_topology.switch_port_table)
        self.switch_ip_address = copy.deepcopy(self.app_topology.switch_ip_address)
        self.init_dpid_info()
        #self.master_process_exec(2,1)
        #self.slave_process_exec(3,2)
        #self.slave_process_exec(2,1)
        #self.master_process_exec(3,2)
        self.ptp_tree(self.graph,2,1)

