
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


