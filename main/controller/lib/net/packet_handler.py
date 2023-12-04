from ryu.lib.packet import arp
from main.dir_server.view.controller_view import insert_edge
from main.controller.manager.traffic_manager import TrafficManager
from main.controller.manager.table_manager import TableManager
from main.dir_server.view.controller_view import insert_node


def handle_arp(controller, msg,
               datapath, in_port, pkt):
    """handle arp pkt

    Args:
        controller: A reference to controller
        msg: the event of packet in
        datapath: the datapath of the switch send packet_in msg
        in_port: the port of the switch the pkt come in
        pkt: the pkt information
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    pkt_arp = pkt.get_protocol(arp.arp)
    if pkt_arp.opcode == arp.ARP_REQUEST:
        controller.logger.info("ARP_REQUEST")
        handle_arp_request(controller=controller,
                           msg=msg, datapath=datapath,
                           in_port=in_port, pkt=pkt)
    elif pkt_arp.opcode == arp.ARP_REPLY:
        controller.logger.info("ARP_REPLY")
        handle_arp_reply(controller=controller,
                         msg=msg, datapath=datapath,
                         in_port=in_port, pkt=pkt)
    else:
        controller.logger.info("Unknown ARP opcode")


def handle_arp_request(controller, msg, datapath,
                       in_port, pkt):
    """handle arp request pkt

    if the request ip is in the topology, send arp reply quickly
    else flood the arp request

    Args:
        controller: The controller's reference
        msg: the event of packet in
        datapath: the datapath of the switch send packet_in msg
        in_port: the port of the switch the pkt come in
        pkt: the pkt information
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    pkt_arp = pkt.get_protocol(arp.arp)
    dpid = datapath.id

    if pkt_arp.src_ip not in controller.hosts_mac:
        # we should flood the packet, but we should flood it according to a span tree
        add_host(controller=controller, mac=pkt_arp.src_mac,
                 ip=pkt_arp.src_ip, dpid=dpid, in_port=in_port)

    if pkt_arp.dst_ip in controller.hosts_mac:
        # If we are here, it means the flow is not installed completely, so
        # we abandon the packet, and later the arp packet will match the flows
        pass
    # Then, just flood it according to the span tree
    data = None
    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
        data = msg.data
    flood(controller=controller, datapath=datapath,
          buffer_id=msg.buffer_id, data=data, in_port=in_port)


def handle_arp_reply(controller, msg, datapath,
                     in_port, pkt):
    """handle arp reply pkt

    Use the traffic manager to install a path, which leads the packet
    to go from source to destination

    Args:
        controller: A reference to controller
        msg: the event of packet in
        datapath: the datapath of the switch send packet_in msg
        in_port: the port of the switch the pkt come in
        pkt: the pkt information
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    pkt_arp = pkt.get_protocol(arp.arp)

    if pkt_arp.src_ip not in controller.hosts_mac:
        dpid = datapath.id
        add_host(controller=controller, mac=pkt_arp.src_mac,
                 ip=pkt_arp.src_ip, dpid=dpid, in_port=in_port)

    # install the flow table and return the data to the switch
    install_packet_road(controller=controller,
                        src=pkt_arp.src_ip,
                        dst=pkt_arp.dst_ip,
                        datapath=datapath,
                        msg=msg,
                        road_type='arp', has_in_port=False)

    controller.logger.info("Handle ARP_REPLY")
    controller.logger.info("src_ip: %s, src_mac: %s, "
                           "dst_ip: %s, dst_mac: %s" %
                           (pkt_arp.src_ip, pkt_arp.src_mac,
                            pkt_arp.dst_ip, pkt_arp.dst_mac))


def send_pkt2switch(controller, datapath, port, pkt):
    """send packet to the switch

    send pkt from controller to the switch and assign an output port

    Args:
        controller: A reference to controller
        datapath: the datapath of the switch send packet_in msg
        port: the port of the switch the pkt come in
        pkt: the pkt information
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    try:
        pkt.serialize()
        data = pkt.data
    except Exception as e:
        controller.logger.error("packet is error")
        data = pkt

    actions = [parser.OFPActionOutput(port=port)]
    out = parser.OFPPacketOut(datapath=datapath,
                              buffer_id=ofproto.OFP_NO_BUFFER,
                              in_port=ofproto.OFPP_CONTROLLER,
                              actions=actions,
                              data=data)
    datapath.send_msg(out)


def add_host(controller, mac: str, ip: str, dpid: str, in_port):
    """add host to the topology

    when an arp or reserve flow come in the switch, add the host which send the pkt to the topology

    Args:
        controller: A reference to controller
        mac: the mac address of the host
        ip: the ip address of the host
        dpid: the dpid of the switch direct connect to the host
        in_port: the port of the switch direct connect to the host
    """
    if ip in controller.hosts_mac:
        return
    controller.hosts_mac[ip] = mac
    # Just write it into the database
    insert_node(controller=controller, name=ip)
    insert_edge(controller=controller,
                src=ip, dst=dpid, src_port=0, dst_port=in_port)


def flood(controller, datapath, in_port,
          buffer_id, data):
    """Flood the packet according to the span tree

    Args:
        controller: The reference to controller
        datapath: The reference to the switch
        in_port: The port which the packet come into the switch
        buffer_id: The buffer id of the packet-out packet
        data: The data of the packet-out packet
    """
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    dpid = datapath.id

    if in_port not in controller.span_tree.in_ports[dpid]:
        return
    out_port = ofproto.OFPP_FLOOD
    actions = [parser.OFPActionOutput(out_port)]
    out = parser.OFPPacketOut(datapath=datapath, buffer_id=buffer_id,
                              in_port=in_port, actions=actions, data=data)
    datapath.send_msg(out)


def simple_l2_switch(controller, msg, datapath,
                     in_port, eth_header, ip_pkt):
    """implement a simple l2 switch

    Args:
        controller: The reference to controller
        msg: the event of packet in
        datapath: the datapath of the switch send packet_in msg
        in_port: the port of the switch the pkt come in
        eth_header: the eth header of the pkt
        ip_pkt: the ip header of pkt
    """
    src = eth_header.src
    dst = eth_header.dst
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    dpid = datapath.id
    controller.mac_to_port.setdefault(dpid, {})

    # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

    # learn a mac address to avoid FLOOD next time.
    controller.mac_to_port[dpid][src] = in_port

    if dst in controller.mac_to_port[dpid]:
        out_port = controller.mac_to_port[dpid][dst]
    else:
        out_port = -1

    data = None
    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
        data = msg.data

    if out_port != -1:
        actions = [parser.OFPActionOutput(out_port)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
        # verify if we have a valid buffer_id, if yes avoid to send both
        # flow_mod & packet_out
        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
            controller.add_flow(datapath, 1, match, actions, msg.buffer_id)
            return
        else:
            controller.add_flow(datapath, 1, match, actions)
    else:
        flood(controller=controller, datapath=datapath, in_port=in_port,
              buffer_id=msg.buffer_id, data=data)


def install_packet_road(controller, src, dst, datapath, msg, road_type,
                        has_in_port=True):
    """Install the packet's road by flow tables

    Args:
        controller: A reference to controller
        src: The source
        dst: The destination
        datapath: The reference to switch
        msg: The packet-in message
        road_type: ipv4 or arp
        has_in_port: Has in_port in match or not
    """
    traffic_manager = TrafficManager(controller=controller)
    src2dst = traffic_manager.find_normal_path(src=src,
                                               dst=dst)
    if not src2dst:
        controller.logger.debug('Can not find the path '
                                'from %s to %s' % (src, dst))
        return
    table_manager = TableManager()
    table_manager.translate_path(graph=traffic_manager.graph, path=src2dst,
                                 switches=controller.datapaths, road_type=road_type,
                                 has_in_port=has_in_port)

    # src = 10.0.0.1, dst = 10.0.0.2
    # src2dst = ['10.0.0.1', 's1', 's2' , '10.0.0.2']
    # src2dst[-2] = 's2', src2dst[-3] = 's1'
    out_port = \
        traffic_manager.graph[src2dst[-2]][src2dst[-3]]['port'][src2dst[-2]]
    send_pkt2switch(controller=controller, datapath=datapath,
                    port=out_port, pkt=msg.data)


def solve_normal_ipv4_packet(controller, msg,
                             datapath, in_port,
                             eth_header, ip_pkt,
                             has_in_port=True):
    """Deal with the normal ipv4 packet

     Args:
        controller: The reference to controller
        msg: the event of packet in
        datapath: the datapath of the switch send packet_in msg
        in_port: the port of the switch the pkt come in
        eth_header: the eth header of the pkt
        ip_pkt: the ip header of pkt
        has_in_port: Has in_port in the match or not
    """
    if ip_pkt.src in controller.hosts_mac \
            and ip_pkt.dst in controller.hosts_mac:
        install_packet_road(controller=controller,
                            msg=msg,
                            datapath=datapath,
                            src=ip_pkt.src,
                            dst=ip_pkt.dst,
                            road_type='ipv4',
                            has_in_port=has_in_port)
        return True
    else:
        if ip_pkt.src not in controller.hosts_mac:
            add_host(controller=controller,
                     mac=eth_header.src, ip=ip_pkt.src,
                     dpid=datapath.id, in_port=in_port)
            if ip_pkt.dst in controller.hosts_mac:
                install_packet_road(controller=controller,
                                    msg=msg,
                                    datapath=datapath,
                                    src=ip_pkt.src,
                                    dst=ip_pkt.dst,
                                    road_type='ipv4',
                                    has_in_port=has_in_port)
                return True
        flood(controller=controller, datapath=datapath,
              in_port=in_port, buffer_id=msg.buffer_id,
              data=msg.data)
    return False
