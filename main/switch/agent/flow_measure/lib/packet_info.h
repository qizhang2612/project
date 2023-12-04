#ifndef _PACKET_INFO_H_
#define _PACKET_INFO_H_
#include <cstdint>

struct Flow
{
    uint8_t protocol;
    uint16_t src_port;
    uint16_t dst_port;
    uint32_t src_ip;
    uint32_t dst_ip;
    Flow() : protocol(0), src_port(0), dst_port(0), src_ip(0), dst_ip(0){};
};

struct Statistics
{
    uint32_t bytes;
    uint32_t count;
};

struct PacketInfo
{
    Flow flow;
    Statistics statistics;
};

#endif // _PACKET_INFO_H_