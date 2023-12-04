#include "capture.h"

void PacketCapture::PacketHandler(u_char *capture, const struct pcap_pkthdr *header, const u_char *packet)
{
    PacketCapture *pkt_capture = reinterpret_cast<PacketCapture *>(capture);
    if (pkt_capture->timer->Exited() || pkt_capture->timer->Paused())
        return;

    PacketInfo pkt_info;
    pkt_info.statistics.count = 1;
    pkt_info.statistics.bytes = header->len;

    struct ether_header *eth_hdr = (struct ether_header *)packet;
    uint16_t eth_type = ntohs(eth_hdr->ether_type);
    packet += ETH_HLEN;
    if (eth_type != ETHERTYPE_IP)
        return;
    struct ip *ip_hdr = (struct ip *)packet;
    pkt_info.flow.src_ip = ntohl(ip_hdr->ip_src.s_addr);
    pkt_info.flow.dst_ip = ntohl(ip_hdr->ip_dst.s_addr);
    pkt_info.flow.protocol = ip_hdr->ip_p;

    packet += (ip_hdr->ip_hl << 2);
    if (ip_hdr->ip_p == IPPROTO_TCP)
    {
        struct tcphdr *tcp = (struct tcphdr *)packet;
        pkt_info.flow.src_port = ntohs(tcp->th_sport);
        pkt_info.flow.dst_port = ntohs(tcp->th_dport);
    }
    else if (ip_hdr->ip_p == IPPROTO_UDP)
    {
        struct udphdr *udp = (struct udphdr *)packet;
        pkt_info.flow.src_port = ntohs(udp->uh_sport);
        pkt_info.flow.dst_port = ntohs(udp->uh_dport);
    }
    // LOG(INFO) << "pcap size: " << pkt_info.statistics.bytes << " protocol: " << int(pkt_info.flow.protocol);
    int w_idx = pkt_capture->timer->GetCurrentWriteIndex();
    pkt_capture->storage_operator[w_idx]->Update(pkt_info);
}

void PacketCapture::CaptureMain()
{
    const static int SNAP_LENGTH = 128;
    const static int BUFSIZE = 268435456;

    char errbuf[PCAP_ERRBUF_SIZE];
    handle = pcap_create(device.c_str(), errbuf);
    if (handle == NULL)
    {
        LOG(INFO) << "create pcap handle failed";
        return;
    }
    pcap_set_snaplen(handle, SNAP_LENGTH);
    pcap_set_buffer_size(handle, BUFSIZE);
    pcap_set_promisc(handle, 1);
    pcap_set_immediate_mode(handle, 1);
    pcap_setdirection(handle, PCAP_D_IN);
    if (pcap_activate(handle) < 0)
    {
        LOG(INFO) << "Couldn't activate pcap";
        pcap_close(handle);
        return;
    }
    pcap_loop(handle, -1, PacketCapture::PacketHandler, (u_char *)this);
    pcap_close(handle);
    LOG(INFO) << "capture thread stopped";
}

void PacketCapture::StartPacketProcess()
{
    LOG(INFO) << "start capture thread, device: " << device;
    capture_thread = std::thread(&PacketCapture::CaptureMain, this);
}

void PacketCapture::Wait()
{
    capture_thread.join();
}
void PacketCapture::StopCapture()
{
    pcap_breakloop(handle);
}