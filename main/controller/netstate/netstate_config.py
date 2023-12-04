
# ==================link delay=======================
LINK_DELAY_SRC = "10.0.0.111"
LINK_DELAY_DST = "10.0.0.222"
LINK_DELAY_MAC_SRC = "a2:53:30:97:f8:63"
LINK_DELAY_MAC_DST = "06:03:17:58:fb:73"
TS_LEN = 8
ETH_LEN = 14
IP_LEN = 20
UDP_LEN = 8


# ==================link capacity====================
LINK_STATE_PROBE_INTERVAL = 2  # seconds
MAX_PORT_NUM = 10


# ===================flow measure=====================
LISTEN_PORT = 7777
LISTEN_ADDRESS = "0.0.0.0"
# srcIP dstIP srcPort dstPort protocol size num
copy_len = [4, 4, 2, 2, 1, 4, 4]
# 超时时间
storage_time_out = 10*60  # 10 minute, 600s
# mysql config
host = "127.0.0.1"
user = "root"
password = "123456"
port = 3306
database = "flow_measure"
table_name = "measure_data"
col = ['src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol', 'size', 'num', 'begin_time', 'end_time']
col_type = ['varchar(16)', 'varchar(16)', 'int', 'int', 'int', 'int', 'int', 'bigint', 'bigint']
insert_sql = '''
    insert into {}(src_ip, dst_ip, src_port, dst_port, protocol, size, num, begin_time, end_time) 
    values(%s, %s, %s, %s, %s, %s, %s, %s, %s)
'''.format(table_name)

# ===================anomaly detection=====================
# 各个测量阈值
DDOS_TEST_PERIOD = 1  # DDoS检测周期
HEAVY_HITTER_THREASHOLD = 30000000  # 大流判定比特数>阈值
HEAVY_CHANGE_THREASHOLD = 200  # 频繁改变流比特数>阈值
DDOS_ENTROPY_THREASHOLD = 1.1       # DDoS判定信息熵<阈值，两个节点占据全部带宽算攻击
DDOS_PACKET_NO_THREASHOLD = 10000   # 每1秒1万包算攻击
DDOS_FLOW_NO_THREASHOLD = 5     # 流数目>阈值10000条流
PACKET_LOSS_DETECT_RATIO = 0.1      #丢包率阈值
PACKET_LOSS_DETECT_MAC_SRC = "a2:53:30:97:f9:63"
PACKET_LOSS_DETECT_MAC_DST = "06:03:18:58:fb:73"
PACKET_LOSS_DETECT_SRC = "10.0.0.111"
PACKET_LOSS_DETECT_DST = "10.0.0.222"
DETECT_PACKET_NUM = 100

# mysql config
host1 = "127.0.0.1"
user1 = "canal"
password1 = "canal"
port1 = 3306
database1 = "pub_sub"
table_name1 = "error"
table_name2 = "errorflow"
table_name3 = "packetloss"
table_name4 = "ddos"
col1 = ['error_id', 'flow_id', 'happen_time', 'type', 'protocol', 'dpid']
col2 = ['flow_id','src_ip', 'src_port', 'dst_ip', 'dst_port']
col3 = ['packet_loss_id','dpid1','dpid2','happen_time','packet_loss_ratio']
col4 = ['ddos_id','dpid','attacked_ip','happen_time']
col_type1 = ['varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)']
col_type2 = ['varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)']
col_type3 = ['varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)']
col_type4 = ['varchar(16)', 'varchar(16)', 'varchar(16)', 'varchar(16)']
insert_sql1 = '''
    replace into {}(error_id, flow_id, happen_time, type, protocol, dpid) 
    values(%s, %s, %s, %s, %s, %s)
'''.format(table_name1)
insert_sql2 = '''
    replace into {}(flow_id, src_ip, src_port, dst_ip, dst_port) 
    values(%s, %s, %s, %s, %s)
'''.format(table_name2)
insert_sql3 = '''
    replace into {}(packet_loss_id, dpid1, dpid2, happen_time, packet_loss_ratio) 
    values(%s, %s, %s, %s, %s)
'''.format(table_name3)
insert_sql4 = '''
    replace into {}(ddos_id, dpid, attacked_ip, happen_time) 
    values(%s, %s, %s, %s)
'''.format(table_name4)


# ====================global config==================
app_topology_name = 'topology'
app_link_state_name = 'link_state'
app_link_delay_name = 'link_delay'
app_flow_measure_name = 'flow_measure'
app_ptp_clocksync_name = 'ptp_clocksync'
app_packet_loss_detect_name = 'packet_loss_detect'


# ====================controller url==================

# flow measure url
url_flow_measure_base = '/flow_measure'
url_start_flow_measure = url_flow_measure_base + '/start'
url_open_flow_measure = url_flow_measure_base + '/open'
url_close_flow_measure = url_flow_measure_base + '/close'
url_set_frequency = url_flow_measure_base + '/set_frequency'


