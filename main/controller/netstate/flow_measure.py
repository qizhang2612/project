from collections import defaultdict
from ryu.base import app_manager
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3, ether, ofproto_v1_0, ofproto_v1_2
from ryu.ofproto.inet import *
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.app.wsgi import WSGIApplication
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.base.app_manager import lookup_service_brick
from netstate_rest_api import FlowMeasureController
from netstate_config import *
import socket
import selectors
import pymysql
import time
import copy
import networkx
import os
import struct
import urllib.request
import json
import requests
from math import log

db = pymysql.connect(host=host, user=user, password=password, port=port, database=database, charset='utf8')
db1 = pymysql.connect(host=host1, user=user1, password=password1, port=port1, database=database1, charset='utf8')


def int_to_ip(integer):
    """
    Receives an integer ip in host byte order and converts it
    into a string IP address
    Args:
        integer: ip address in host byte order
    Returns:
        string: ip address in x.x.x.x form
    """
    raw = bin(int(integer)).lstrip('0b').zfill(32)
    ip = '%d.%d.%d.%d' % (int(raw[0:8], 2), int(raw[8:16], 2), int(raw[16:24], 2), int(raw[24:32], 2))
    return ip

class FlowData:
    """
    Store measurement information for a traffic flow marked by five tuple
    """
    def __init__(self) -> None:
        """
        size: 字节数
        num: 包数
        begin_time: 流测量数据被第一次上报的时间，使用的是UTC时间，单位是秒
        last_modify: 最后更新流量测量结果的时间 ，使用的是UTC时间，单位是秒
        """
        self.size = 0
        self.num = 0
        self.begin_time = 0
        self.last_modify = 0

class FlowStatics:
    """
    异常分析的每条流的统计数据
    """
    def __init__(self) -> None:
        """
        size: 字节数
        num: 包数
        """
        self.size = 0
        self.num = 0

class TestPeriodMeasureData:
    """
    每个检测周期的流量测量数据
    """
    def __init__(self, dpid) -> None:
        self.dpid = dpid
        self.measure_data = defaultdict(FlowStatics)
    
    def update_measure_data(self, five_tuple, flow_data):
        """
        更新测量信息
        """
        self.measure_data[five_tuple].size += flow_data[0]
        self.measure_data[five_tuple].num += flow_data[1]

class SwitchMeasureData:
    """
    存储和管理某个交换机上报的流量测量信息
    """
    def __init__(self, dpid, address) -> None:
        """
        measure_data
            字典类型，key为五元组(src_ip, dst_ip, src_port, dst_port, protocol)，value
            是FlowData。该变量存储当前交换机上传的所有未超时流的测量信息
        """
        self.dpid = dpid
        self.address = address
        self.measure_data = defaultdict(FlowData)

    def save_to_mysql(self, five_tuple, flow_data: FlowData):
        """
        将一个超时流的测量信息写入mysql数据库，写入时将IP地址转化成字符串形式
        """
        cursor = db.cursor()
        src_ip = int_to_ip(five_tuple[0])
        dst_ip = int_to_ip(five_tuple[1])
        print((src_ip, dst_ip, five_tuple[2], five_tuple[3], five_tuple[4],
               flow_data.size, flow_data.num, flow_data.begin_time, flow_data.last_modify))
        cursor.execute(insert_sql, (src_ip, dst_ip, five_tuple[2], five_tuple[3], five_tuple[4],
                       flow_data.size, flow_data.num, flow_data.begin_time, flow_data.last_modify))
        db.commit()

    def update_measure_data(self, five_tuple, flow_statics, now):
        """
        更新流量的测量信息，更新时检查一下当前流是否已经超时，超时则先将旧的统计信息
        写入mysql数据库，再更新测量信息
        """
        if self.measure_data.get(five_tuple):
            if now - self.measure_data[five_tuple].last_modify >= storage_time_out:
                self.save_to_mysql(five_tuple, self.measure_data[five_tuple])
                self.measure_data[five_tuple].begin_time = now
                self.measure_data[five_tuple].size = 0
                self.measure_data[five_tuple].num = 0
        else:
            self.measure_data[five_tuple] = FlowData()
            self.measure_data[five_tuple].begin_time = now
        self.measure_data[five_tuple].size += flow_statics[0]
        self.measure_data[five_tuple].num += flow_statics[1]
        self.measure_data[five_tuple].last_modify = now


class FlowMeasure(app_manager.RyuApp):
    _CONTEXTS = {'wsgi': WSGIApplication}
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]
    """
    接收交换机上传的测量数据，维护和管理流量测量结果
    1. 设置epoll线程负责监听来自交换机的上报数据，同步更新测量结果
    2. 设置超时检测线程定时查询当前维护的所有流的测量信息是否超时，超时则写入mysql数据库
    """
    def __init__(self, *_args, **_kwargs):
        """
        fd_to_address: 交换机上传测量结果的连接和上传时所用的IP地址之间的映射
        fd_to_dpid: 交换机上传测量结果的连接和交换机id之间的映射
        dpid_to_addr：dpid和交换机IP地址之间的映射
        switch_measure_data: 字典，维护所有交换机的测量数据
        work_thread: epoll线程
        timeout_detection_thread：超时检测线程
        """
        super().__init__(*_args, **_kwargs)
        wsgi = _kwargs['wsgi']
        wsgi.register(FlowMeasureController, {app_flow_measure_name: self})
        self.name = app_flow_measure_name
        # 依赖topology生成的网络拓扑
        self.app_topology = app_manager.lookup_service_brick(app_topology_name)
        self.graph = networkx.graph.Graph()  # 网络拓扑结构
        self.flow_entries = {}  # 存流表
        self.route_table = {}  # 存路由表
        self.link_to_port = {}
        self.error_id = 0
        self.flow_id = 0
        self.ddos_id = 0

        self.fd_to_address = {}
        self.fd_to_dpid = {}
        self.dpid_to_addr = {}
        self.datapaths = {}
        self.switch_measure_data = defaultdict(SwitchMeasureData)
        self.new_measure_data = defaultdict(TestPeriodMeasureData)
        self.old_measure_data = defaultdict(TestPeriodMeasureData)
        self.work_thread = hub.spawn(self.listen_measure_data_upload)
        self.timeout_detection_thread = hub.spawn(self._timeout_detection)
        self.ddos_inspect_thread = hub.spawn(self._ddos_inspect_test)
        cursor = db.cursor()
        cmd = ''
        for i in range(len(col)):
            cmd += col[i] + " " + col_type[i] + ","
        cmd = cmd[:-1]
        cursor.execute("create table if not exists {}({})".format(table_name, cmd))
        db.commit()

    def _timeout_detection(self):
        while True:
            now = int(time.time())
            # 遍历所有交换机的流信息
            for dpid, switch_measure_data in self.switch_measure_data.items():
                del_list = []
                # 遍历交换机每条流的信息
                for five_tuple, flow_data in switch_measure_data.measure_data.items():
                    if now - flow_data.last_modify >= storage_time_out:
                        switch_measure_data.save_to_mysql(five_tuple, flow_data)
                        del_list.append(five_tuple)
                for f_tuple in del_list:
                    del self.switch_measure_data[dpid].measure_data[f_tuple]
            hub.sleep(60)

    def save_to_mysql(self, dpid, five_tuple, happen_time, error_type, protocol):
        """
        将异常信息写入mysql数据库，写入时将IP地址转化成字符串形式
        """
        cursor = db1.cursor()
        src_ip = int_to_ip(five_tuple[0])
        dst_ip = int_to_ip(five_tuple[1])
        cursor.execute(insert_sql1, (str(self.error_id), str(self.flow_id), happen_time, str(error_type), protocol, str(dpid)))
        cursor.execute(insert_sql2, (str(self.flow_id), src_ip, str(five_tuple[2]), dst_ip, str(five_tuple[3])))
        self.error_id = self.error_id + 1
        self.flow_id = self.flow_id + 1
        db1.commit()

    def save_to_mysql_ddos(self, dpid, attacked_ip, happen_time):
        """
        将异常信息写入mysql数据库，写入时将IP地址转化成字符串形式
        """
        cursor = db1.cursor()
        cursor.execute(insert_sql4, (str(self.ddos_id), str(dpid), happen_time, attacked_ip))
        self.ddos_id = self.ddos_id + 1
        db1.commit()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handle(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath
        self.logger.info("flow measure config dpid %d", datapath.id)
        self.dpid_to_addr[datapath.id] = datapath.address

    def _parse_flow_data(self, data: bytes):
        pos = 0
        content = []
        for i in copy_len:
            content.append(int.from_bytes(data[pos:pos+i], byteorder='little'))
            pos = pos + i
        content = tuple(content)
        return content[0:5], content[5:]

    def _handle_recv_data(self, data: bytes, dpid: int):
        """
        从字节序列中解析出五元组，更新测量数据
        Args:
            data (bytes): 交换机上传的测量数据
            dpid (int): 交换机ID
        """
        unit_len = sum(copy_len)
        now = int(time.time())
        for i in range(0, len(data), unit_len):
            if i + unit_len > len(data):
                break
            five_tuple, flow_statics = self._parse_flow_data(data[i:i+unit_len])
            #self.logger.info("测量数据：{}, {}".format(five_tuple, flow_statics))
            self.switch_measure_data[dpid].update_measure_data(five_tuple, flow_statics, now)
            self.new_measure_data[dpid].update_measure_data(five_tuple,flow_statics)

    def _read(self, epoll: selectors.DefaultSelector, conn):
        """
        在accept时注册的读事件到来时调用该函数，从缓冲区中拿走数据。交换机利用tcp连接上传
        测量数据，所有数据都是按照小端（主机字节序）存放，测量数据上传的格式如下：
            -----------------------------------------------------------------------
            |count| src_ip | dst_ip | src_port | dst_port | protocol | size | num |
            -----------------------------------------------------------------------
        count代表此次上传多少组（一个五元组代表一组）数据，因此在读测量数据时，需要严格根据count来取数据，
        否则会因为tcp的粘包问题导致数据取出来不完整
        """
        # 当有数据到来时，首先取头四个字节的数据，即count字段
        data = conn.recv(4)
        if not data:
            # 数据为空，则代表这是一次连接关闭请求，从记录中删除该连接的信息
            # self.logger.info("client %s close", self.fd_to_address[conn.fileno()])
            epoll.unregister(conn)
            del self.fd_to_address[conn.fileno()]
            del self.fd_to_dpid[conn.fileno()]
            conn.close()
        else:
            # 根据count字段知道上传了多少组数据，计算接下来应该要从缓冲区拿的字节数，再从缓冲区
            # 获取数据，调用处理函数解析测量结果
            flow_num = int.from_bytes(data, byteorder='little')
            measure_data = conn.recv(flow_num*sum(copy_len))
            # 运行时可能会在此处报错 key error，原因是没有及时收集到连接过来的交换机的dpid和addr
            # 的对应关系，导致accept时找不到连接所属的dpid，无法在self.fd_to_dpid添加表项
            self._handle_recv_data(data=measure_data, dpid=self.fd_to_dpid[conn.fileno()])

    def _accept(self, epoll: selectors.DefaultSelector, sock):
        """
        新的连接进来时，注册该连接的读事件监听，为该连接所属的交换机创建测量数据管理对象（SwitchMeasureData）
        """
        conn, address = sock.accept()
        # print("new connection {}".format(address))
        conn.setblocking(False)
        # 注册监听事件：有数据到来
        epoll.register(conn, selectors.EVENT_READ, self._read)
        self.fd_to_address[conn.fileno()] = address[0]
        # 查找该连接所属交换机,如果是新进来的则创建测量数据
        for dpid, addr in self.dpid_to_addr.items():
            if addr[0] == address[0]:
                self.fd_to_dpid[conn.fileno()] = dpid
                if not self.new_measure_data.get(dpid):
                    self.new_measure_data[dpid] = TestPeriodMeasureData(dpid=dpid)
                if not self.old_measure_data.get(dpid):
                    self.old_measure_data[dpid] = TestPeriodMeasureData(dpid=dpid)
                if not self.switch_measure_data.get(dpid):
                    self.switch_measure_data[dpid] = SwitchMeasureData(dpid=dpid, address=addr)
                break

    def listen_measure_data_upload(self):
        """
        建立接收socket，监听测量数据上报
        """
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((LISTEN_ADDRESS, LISTEN_PORT))
        server_sock.listen(20)
        self.logger.info("listen measure data in %s:%d", LISTEN_ADDRESS, LISTEN_PORT)

        server_sock.setblocking(False)
        epoll = selectors.DefaultSelector()
        epoll.register(server_sock, selectors.EVENT_READ, self._accept)
        time_out = 1
        while True:
            events = epoll.select(time_out)
            if not events:
                continue
            for key, mask in events:
                callback = key.data
                callback(epoll, key.fileobj)

    def set_zero(self):
        """
        将self.new_measure_data置空
        """
        for dpid, test_measure_data in self.new_measure_data.items():
            for five_tuple, flow_data in test_measure_data.measure_data.items():
                flow_data.num = 0
                flow_data.size = 0

    # 周期更新一次流表，为了得到正确路由信息，然后进行路由错误检测
    def discover_flow_entries(self):
        ret = self.get_flow_entries_ev(None)
        if ret == 0:
            self.get_route_table()
            self.routing_path_test()
            #self.logger.info(self.flow_entries)
            #self.logger.info(self.route_table)
        elif ret == -1:
            self.logger.info('get flow entries failed, so I do not get route table and not test routing path')
        else:
            assert (False)

    def get_flow_entries(self, dpid):
        #self.logger.info('get_flow_entries')
        try:
            url = "http://127.0.0.1:8080/stats/flow/" + str(dpid)
            req = urllib.request.Request(url)
            res_data = urllib.request.urlopen(req)
            res = res_data.read()
            res = json.loads(res)
            return res
        except Exception as e:
            print(e)
            return None

    # 获取流表
    #@set_ev_cls([ofp_event.EventOFPFlowRemoved, ofp_event.EventOFPFlowMod], MAIN_DISPATCHER)
    def get_flow_entries_ev(self, ev):
        flow_entries = {}
        # FIXME：可能有changed size问题，也许能用list()解决，不知道行不行
        for dpid in self.datapaths.keys():
            res = self.get_flow_entries(dpid)
            if res == None:
                return -1
            for dpid_str in res:
                flow_entries[int(dpid_str)] = res[dpid_str]
        self.flow_entries = copy.deepcopy(flow_entries)
        return 0

    # TODO:FIXME: 从流表变路由表
    def get_route_table(self):
        route_table = {}
        for dpid_int in self.flow_entries.keys():
            route_table[dpid_int] = {}
            flow_entry_list = self.flow_entries[dpid_int]
            for flow_enrty in flow_entry_list:
                # print(flow_enrty, type(flow_enrty))
                port_no_int = 0
                nw_dst_str = ""

                if "actions" in flow_enrty:
                    action_list = flow_enrty["actions"]
                    for action in action_list:
                        if isinstance(action, str):
                            x = action.split(":", 2)
                            #self.logger.info(x)
                            if x[0] == 'OUTPUT' and x[1] != 'CONTROLLER'and x[1] != 'LOCAL':
                                port_no_int = int(x[1])  # 转发端口
                                break
                        elif isinstance(action, dict):
                            if action["type"] == "OUTPUT" and action["port"] != 'CONTROLLER':
                                port_no_int = int(action["port"])
                                break
                else:
                    continue

                if "match" in flow_enrty:
                    match_dict = flow_enrty["match"]
                    if "nw_dst" in match_dict:
                        nw_dst_str = match_dict["nw_dst"]
                        route_table[dpid_int][nw_dst_str] = port_no_int  # 根据dpid和目的ip决定其转发端口(int)

        self.route_table = copy.deepcopy(route_table)

    def get_first_switch(self, five_tuple):
        #得到第一个交换机ID
        srcip = int_to_ip(five_tuple[0])
        for dpid in self.datapaths.keys():
            if srcip == self.dpid_to_addr[dpid][0]:
                return dpid
            else:
                continue
        return None

    def get_last_switch(self, five_tuple):
        #得到最后一个交换机ID
        dstip = int_to_ip(five_tuple[1])
        for dpid in self.datapaths.keys():
            if dstip == self.dpid_to_addr[dpid][0]:
                return dpid
            else:
                continue
        return None

    def get_neighbors(self, dpid):
        #获得邻居交换机节点号码 
        return networkx.all_neighbors(self.graph, dpid)

    def is_in_this(self,every_measure_data,dp_id,flow):
        for dpid, test_measure_data in every_measure_data.items():
            if dpid == dp_id:
                for five_tuple, flow_data in test_measure_data.measure_data.items():
                    if five_tuple == flow:
                        return True
                    else:
                        continue 
            else:
                continue
        return False

    # 周期检测HH
    def heavy_hitter(self, BitThreshold):
        HeavyHitter = {}#存储大流信息
        #解决dictionary changed size during iteration问题
        new_measure_data = copy.deepcopy(self.new_measure_data)
        for dpid, test_measure_data in new_measure_data.items():
            for five_tuple, flow_data in test_measure_data.measure_data.items():
                if(flow_data.size > BitThreshold):
                    if(five_tuple[4] == 6):
                        protocol = "TCP"
                    else:
                        protocol = "UDP"
                    hh_result = '从交换机' + str(dpid) + '上报的流数据中检测到Heavy Hitter异常流量-从' \
                                + int_to_ip(five_tuple[0]) \
                                + '的' + str(five_tuple[2]) + '端口发到' \
                                + int_to_ip(five_tuple[1]) \
                                + '的' + str(five_tuple[3]) + '端口的' \
                                + protocol + '包的流量超过阈值' + str(HEAVY_HITTER_THREASHOLD) + '。'
                    hh_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    self.logger.info('result: %s\ncreate_time: %s\n', hh_result, hh_create_time)
                    HeavyHitter[dpid] = {five_tuple, hh_create_time}
                    self.save_to_mysql(dpid,five_tuple,hh_create_time,1,protocol)
        return HeavyHitter

    # 周期检测HC
    def heavy_change(self,BitChangeThreshold):
        HeavyChange = {}#存储大流变化信息
        thisbit = {}
        lastbit = {}
        new_measure_data = copy.deepcopy(self.new_measure_data)
        old_measure_data = copy.deepcopy(self.old_measure_data)
        for dpid, test_measure_data in new_measure_data.items():
            for five_tuple, flow_data in test_measure_data.measure_data.items():
                thisbit[dpid] = {five_tuple:flow_data.size}
        for dpid, test_measure_data in old_measure_data.items():
            for five_tuple, flow_data in test_measure_data.measure_data.items():
                lastbit[dpid] = {five_tuple:flow_data.size}
        for dpid in thisbit.keys() & lastbit.keys():
            for flow in thisbit[dpid].keys() & lastbit[dpid].keys():
                bit_change = abs(thisbit[dpid][flow]-lastbit[dpid][flow])
                #self.logger.info(bit_change)
                if bit_change > BitChangeThreshold:
                    if(five_tuple[4] == 6):
                        protocol = "TCP"
                    else:
                        protocol = "UDP"
                    hc_result = '从交换机' + str(dpid) + '上报的流数据中检测到Heavy Change异常流量-在时间' \
                                + str(DDOS_TEST_PERIOD * 2) + '秒内从' \
                                + int_to_ip(flow[0]) \
                                + '的' + str(flow[2]) + '端口发到' \
                                + int_to_ip(flow[1]) \
                                + '的' + str(flow[3]) + '端口的' \
                                + protocol + '包的流量变化超过阈值' + str(HEAVY_CHANGE_THREASHOLD*10000) + '。'
                    hc_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    self.logger.info('result: %s\ncreate_time: %s\n', hc_result, hc_create_time)
                    HeavyChange[dpid] = {flow,hc_create_time}
                    #dpid, five_tuple, happen_time, error_type, protocol
                    self.save_to_mysql(dpid,flow,hc_create_time,2,protocol)
        return HeavyChange

    #异常检测执行函数
    def _ddos_inspect_test(self):
        hub.sleep(15)
        while True:
            self.graph = copy.deepcopy(self.app_topology.graph)
            self.link_to_port = copy.deepcopy(self.app_topology.link_to_port)
            #self.logger.info(self.link_to_port.keys())
            for dpid in self.datapaths.keys() :
                self.ddos_inspect_test(dpid)
            self.discover_flow_entries()
            #self.logger.info(self.dpid_to_addr)
            self.heavy_hitter(HEAVY_HITTER_THREASHOLD)
            self.heavy_change(HEAVY_CHANGE_THREASHOLD)
            self.old_measure_data = copy.deepcopy(self.new_measure_data)
            self.set_zero()
            hub.sleep(DDOS_TEST_PERIOD)

    def ddos_inspect(self, dp_id):
        # 计算香农熵
        num_entries = 0.0  # 总包数
        label_counts = {}
        flow_count = 0
        new_measure_data = copy.deepcopy(self.new_measure_data)
        for dpid, test_measure_data in new_measure_data.items():
            if(dpid == dp_id):
                for five_tuple, flow_data in test_measure_data.measure_data.items():
                    if new_measure_data[dpid].measure_data[five_tuple].num > 0:
                        flow_count += 1
                        current_label = five_tuple[1]  # 对目的IP进行熵计算。
                        if current_label not in label_counts.keys():
                            label_counts[current_label] = 0
                        packetcount = new_measure_data[dpid].measure_data[five_tuple].num
                        label_counts[current_label] += packetcount
                        num_entries += packetcount
            else:
                continue
        if num_entries == 0:
            return None
        shannon_ent = 0.0  # 香农熵
        for key in label_counts:
            if label_counts[key] > 0:
                try:
                    prob = float(label_counts[key]) / num_entries  # 该目的ip的概率
                    shannon_ent -= prob * log(prob, 2)  # 香农熵
                except ValueError as e:
                    shannon_ent = -1
        attacked_ip = max(label_counts, key=label_counts.get)  # 将作为dstIP最多的包的IP标记为被ddos攻击IP
        return (shannon_ent, num_entries, flow_count, attacked_ip)

    # ddos加上流数目阈值，防止误报正常流量。
    def ddos_inspect_test(self, dp_id):
        ddos = self.ddos_inspect(dp_id)
        self.logger.info(ddos)
        if ddos == None:
            return None
        # 信息熵如果小于阈值，包数大于阈值，流数大于阈值，则判定发生了DDoS攻击
        #self.logger.info(ddos)
        if ddos[0] < DDOS_ENTROPY_THREASHOLD and ddos[1] > DDOS_PACKET_NO_THREASHOLD and ddos[
            2] >= DDOS_FLOW_NO_THREASHOLD:
            attacked_ip = int_to_ip(ddos[3])
            dd_result = '从交换机' + str(dp_id) + '上报的流数据中检测到DDoS攻击-主机' \
                        + int_to_ip(ddos[3]) \
                        + '遭到DDoS攻击。'
            dd_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            self.logger.info('result: %s\ncreate_time: %s\n', dd_result, dd_create_time)
            self.save_to_mysql_ddos(dp_id,dd_create_time,attacked_ip)

    def routing_path_test(self):
        # 先找真实路径，找完再比对
        # 检测全部流
        self.route_err = False
        route_err = False
        new_measure_data = copy.deepcopy(self.new_measure_data)
        for dpid, test_measure_data in new_measure_data.items():
            for five_tuple, flow_data in test_measure_data.measure_data.items():
                prev_id = self.get_first_switch(five_tuple)
                correct_prev_id = prev_id
                if prev_id not in self.datapaths.keys():
                    break
                if self.is_in_this(self.new_measure_data,prev_id,five_tuple) != True:
                    continue
                prev_bit_size = flow_data.size
                last_id = self.get_last_switch(five_tuple)
                correct_last_id = last_id
                path = [prev_id]  # 真实路径
                stop = False
                hops = 1
                # XXX： 如果路由错误，导致数据包没有走到最后一个交换机，报黑洞错误不报路由错误
                while not stop and prev_id != last_id and hops < 20:  
                    stop = True
                    for neighbor_id in self.get_neighbors(prev_id):
                        if neighbor_id in path:
                            continue
                        if neighbor_id not in self.datapaths.keys():
                            continue
                        for dp_id, test_measure_data1 in new_measure_data.items():
                            if dp_id == neighbor_id:
                                for flow, flow_data1 in test_measure_data1.measure_data.items():
                                    if flow == five_tuple and abs((flow_data1.size - prev_bit_size) / (float)(prev_bit_size)) < 0.3 and prev_bit_size > 1000000:
                                        path.append(neighbor_id)
                                        prev_id = neighbor_id
                                        prev_bit_size = flow_data1.size
                                        stop = False
                                        hops += 1
                                    else:
                                        continue
                        if prev_id == neighbor_id:
                            break
                # # got real path

                # find correct path
                nw_dst_str = int_to_ip(five_tuple[1])
                correct_path = [correct_prev_id]  # 正确路径
                special_ip = False
                while correct_prev_id != correct_last_id:
                    if nw_dst_str not in self.route_table[correct_prev_id].keys():
                        special_ip = True
                        break
                    correct_next_port_no_int = self.route_table[correct_prev_id][nw_dst_str]
                    if correct_next_port_no_int not in switch_port_table[correct_prev_id]:
                        special_ip = True
                        break
                    correct_next_dpid = self.link_to_port[(correct_prev_id,correct_next_port_no_int)][0]
                    correct_path.append(correct_next_dpid)
                    correct_prev_id = correct_next_dpid
                # got correct path

                if special_ip:
                    continue
                if path == correct_path:
                    continue
                route_err = False
                if hops > 15:
                    route_err = True
                pathlen = len(path)
                cpathlen = len(correct_path)
                blace_hole_err = False
                if pathlen > cpathlen:
                    route_err = True
                else:
                    assert (pathlen <= cpathlen)
                    for i in range(pathlen):
                        if path[i] != correct_path[i]:
                            route_err = True
                        else:
                            continue
                    blace_hole_err = True

                if route_err:
                    if(five_tuple[4] == 6):
                        protocol = "TCP"
                    else:
                        protocol = "UDP"
                    ly_result = '检测到路由错误-交换机' + str(dpid) + '中存在路由表错误-从' \
                                + int_to_ip(five_tuple[0]) \
                                + '的' + str(five_tuple[2]) + '端口发到' \
                                + int_to_ip(five_tuple[1]) \
                                + '的' + str(five_tuple[3]) + '端口的' \
                                + protocol + '包的路径为交换机' + str(path) + '是错误的，正确的路径应该为交换机' \
                                + str(correct_path)
                    ly_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    self.logger.info('result: %s\ncreate_time: %s\n', ly_result, ly_create_time)
                    self.route_err = True
                    self.save_to_mysql(dpid,five_tuple,ly_create_time,3,protocol)
                else:
                    assert (not self.route_err)
                    if stop and flow_data.num > 20000 and blace_hole_err:
                        # 报告黑洞 XXX
                        if(five_tuple[4] == 6):
                            protocol = "TCP"
                        else:
                            protocol = "UDP"
                        hd_result = '检测到黑洞-从' \
                                    + int_to_ip(five_tuple[0])\
                                    + '的' + str(five_tuple[2]) + '端口发到' \
                                    + int_to_ip(five_tuple[1]) \
                                    + '的' + str(five_tuple[3]) + '端口的' \
                                    + protocol + '包发生黑洞。'
                        hd_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        self.logger.info('result: %s\ncreate_time: %s\n', hd_result, hd_create_time)
                        self.save_to_mysql(dpid,five_tuple,hd_create_time,4,protocol)
                        continue