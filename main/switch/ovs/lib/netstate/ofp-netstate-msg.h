#ifndef _OFP_NETSTATE_MSG_H_
#define _OFP_NETSTATE_MSG_H_
#include "openvswitch/ofpbuf.h"
#include "openvswitch/ofp-errors.h"
#include "netstate-struct.h"
#include "utils.h"
#include <rte_byteorder.h>


#define OFP_PAYLOAD_OFFSET 16
typedef struct setFrequencyMsg
{
    ovs_be64 period;
    ovs_be64 interval;
    ovs_be64 duration;
} setFrequencyMsg;

typedef struct setForceQuitMsg
{
    uint8_t force_quit;
} setForceQuitMsg;

void set_force_quit_handler(void *dst, void *msg);
void request_measure_handler(void *dst, void *msg);
void set_frequency_handler(void *dst, void *msg);

enum ofperr parse_set_force_quit(uint8_t *packet, uint32_t pkt_len);
enum ofperr parse_request_measure(uint8_t *packet, uint32_t pkt_len);
enum ofperr parse_set_frequency(uint8_t *packet, uint32_t pkt_len);

#endif // _OFP_NETSTATE_MSG_H_