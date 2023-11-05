#ifndef _OFP_ANTS_MSG_H_
#define _OFP_ANTS_MSG_H_
#include "netstate/ofp-netstate-msg.h"

#define ANTS_VENDER_ID 0x00006090

enum antsSubtype
{
    NET_STATE_REQUEST_MEASURE,
    NET_STATE_SET_FREQUENCY,
    NET_STATE_SET_FORCE_QUIT
};

enum ofperr handle_ants_messages(uint8_t *packet, uint32_t pkt_len, uint32_t sub_type);

#endif // _OFP_ANTS_MSG_H_