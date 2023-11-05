from collections import defaultdict
from ryu.base import app_manager
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3, ether, ofproto_v1_0, ofproto_v1_2
from ryu.ofproto.inet import *
from netstate_config import *
import socket
import selectors
import pymysql
import time
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.app.wsgi import WSGIApplication
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from netstate_rest_api import FlowMeasureController

db = pymysql.connect(host=host, user=user, password=password, port=port, database=database, charset='utf8')


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
        self.fd_to_address = {}
        self.fd_to_dpid = {}
        self.dpid_to_addr = {}
        self.datapaths = {}
        self.switch_measure_data = defaultdict(SwitchMeasureData)
        self.work_thread = hub.spawn(self.listen_measure_data_upload)
        self.timeout_detection_thread = hub.spawn(self._timeout_detection)
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
            self.logger.info("测量数据：{}, {}".format(five_tuple, flow_statics))
            self.switch_measure_data[dpid].update_measure_data(five_tuple, flow_statics, now)

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
