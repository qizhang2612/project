#ifndef _LINK_DELAY_H_
#define _LINK_DELAY_H_
#include <stdlib.h>
#include <inttypes.h>
#include <stdbool.h>
#include <string.h>
#include "utils.h"
#include "dp-packet.h"
#include "packets.h"
#include "netstate-struct.h"

/*src ip and dst ip of link delay detect packet*/
extern ovs_be32 detect_pkt_src;
extern ovs_be32 detect_pkt_dst;

void init_link_delay();
void write_timestamp(struct dp_packet *packet);
bool is_detect_packet_st(void *packet);
void write_timestamp_st(void *packet);
static inline bool is_udp_packet(struct dp_packet *packet)
{
    return ((struct ip_header *)dp_packet_l3(packet))->ip_proto == IPPROTO_UDP;
}
static inline bool is_link_delay_pkt(struct dp_packet *packet)
{
    return is_udp_packet(packet) && is_detect_packet_st(dp_packet_data(packet));
}

#endif // _LINK_DELAY_H_