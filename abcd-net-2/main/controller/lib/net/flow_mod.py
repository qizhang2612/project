from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, ofproto_v1_2, ofproto_v1_0
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp, ipv4
from ryu.ofproto.inet import IPPROTO_ICMP, IPPROTO_TCP, IPPROTO_UDP


class FlowMod(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super().__init__(*_args, **_kwargs)
        self.logger.info("create instance of flow mod")

    def _add_flow(self, datapath, priority, match, actions, idle_timeout=60, hard_timeout=10000, table_id=0):
        dp = datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=dp, priority=priority,
            command=ofp.OFPFC_ADD,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            match=match, instructions=inst, table_id=table_id)
        dp.send_msg(mod)

    def send_flow_mod_ip(self, datapath, src_ip, dst_ip, in_port, out_port, priority=1):
        self.logger.info("send_flow_mod_ip")
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(in_port=in_port, eth_type=0x800, ipv4_src=src_ip, ipv4_dst=dst_ip)
        actions = [parser.OFPActionOutput(out_port)]
        self._add_flow(datapath=datapath, priority=priority, match=match, actions=actions)

    def send_flow_mod_tcp(self, datapath, src_ip, dst_ip, in_port, out_port, tcp_dst, priority=1):
        print("send_flow_mod_tcp")
        dp = datapath
        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            in_port=in_port, eth_type=0x800, ipv4_src=src_ip, ipv4_dst=dst_ip,
            ip_proto=IPPROTO_TCP, tcp_dst=tcp_dst)
        actions = [parser.OFPActionOutput(out_port)]
        self._add_flow(datapath=dp, priority=priority, match=match, actions=actions)

    def send_flow_mod_udp(self, datapath, src_ip, dst_ip, in_port, out_port, udp_dst, priority=1):
        print("send_flow_mod_udp")
        dp = datapath
        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            in_port=in_port, eth_type=0x800, ipv4_src=src_ip, ipv4_dst=dst_ip,
            ip_proto=IPPROTO_UDP, udp_dst=udp_dst)
        actions = [parser.OFPActionOutput(out_port)]
        self._add_flow(datapath=dp, priority=priority, match=match, actions=actions)

    def delete_flow_table(self, datapath, src_ip, dst_ip, in_port, out_port, dst_port, protocol):
        print("del: src_ip:{}, dst_ip{}, in_port:{}, out_port:{}, dst_port:{}"
              .format(src_ip, dst_ip, in_port, out_port, dst_port))
        dp = datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        cookie = 0
        cookie_mask = 0
        table_id = 0
        priority = 1
        buffer_id = ofp.OFP_NO_BUFFER
        if protocol == IPPROTO_TCP:
            match = parser.OFPMatch(
                eth_type=0x800, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=protocol, in_port=in_port, tcp_dst=dst_port)
        else:
            match = parser.OFPMatch(
                eth_type=0x800, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=protocol, in_port=in_port, udp_dst=dst_port)
        inst = []
        flow_mod = parser.OFPFlowMod(
            datapath=dp, cookie=cookie, cookie_mask=cookie_mask, table_id=table_id,
            command=ofp.OFPFC_DELETE, idle_timeout=0, hard_timeout=0, priority=priority, buffer_id=buffer_id,
            out_port=out_port, out_group=ofp.OFPG_ANY, flags=ofp.OFPFF_SEND_FLOW_REM,
            match=match, instructions=inst)
        dp.send_msg(flow_mod)
