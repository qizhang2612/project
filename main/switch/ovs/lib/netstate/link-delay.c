#include <config.h>
#include <libconfig.h>
#include <arpa/inet.h>
#include "link-delay.h"
#include "openvswitch/vlog.h"
VLOG_DEFINE_THIS_MODULE(link_delay);

ovs_be32 detect_pkt_src;
ovs_be32 detect_pkt_dst;

void init_link_delay()
{
    config_t cfg;
    int count;
    config_init(&cfg);
    if (!config_read_file(&cfg, netstate_config_file))
    {
        VLOG_ERR("INIT LINK DELAY ERRORE!");
        config_destroy(&cfg);
        abort();
    }

    config_setting_t *ip_info = config_lookup(&cfg, "link_delay");
    count = config_setting_length(ip_info);
    ovs_assert(count == 2);
    const char *src;
    const char *dst;
    if (!(config_setting_lookup_string(ip_info, "src_ip", &src) &&
          config_setting_lookup_string(ip_info, "dst_ip", &dst)))
        abort();
    VLOG_INFO("link delay src:%s, dst:%s", src, dst);
    detect_pkt_src = inet_addr(src);
    detect_pkt_dst = inet_addr(dst);

    config_destroy(&cfg);
}

void write_timestamp(struct dp_packet *packet)
{
    VLOG_INFO("link delay captured");
    uint8_t count;
    uint8_t *data;
    uint32_t offset;
    uint64_t now;
    data = dp_packet_get_udp_payload(packet);
    count = *data;
    offset = sizeof(uint64_t) * count + 1;
    now = tsc_to_us(rdtsc());
    *(uint64_t *)(data + offset) = rte_cpu_to_be_64(now);
    *data = count + 1;
}

bool is_detect_packet_st(void *packet)
{
    struct eth_header *l2;
    struct ip_header *l3;
    l2 = (struct eth_header *)packet;
    if (likely(l2->eth_type == htons(ETH_TYPE_IP)))
    {
        l3 = (struct ip_header *)(packet + ETH_HEADER_LEN);
        return get_16aligned_be32(&(l3->ip_src)) == detect_pkt_src &&
               get_16aligned_be32(&(l3->ip_dst)) == detect_pkt_dst;
    }
    return false;
}

void write_timestamp_st(void *packet)
{
    VLOG_INFO("link delay captured");
    uint8_t *udp_payload;
    uint8_t count;
    uint32_t offset;
    uint64_t now;
    udp_payload = (uint8_t *)(packet + ETH_HEADER_LEN + IP_HEADER_LEN + UDP_HEADER_LEN);
    count = *udp_payload;
    offset = sizeof(uint64_t) * count + 1;
    now = tsc_to_us(rdtsc());
    *(uint64_t *)(udp_payload + offset) = rte_cpu_to_be_64(now);
    *udp_payload = count + 1;
}