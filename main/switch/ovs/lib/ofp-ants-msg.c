#include "ofp-ants-msg.h"

enum ofperr handle_ants_messages(uint8_t *packet, uint32_t pkt_len, uint32_t sub_type)
{
    switch (sub_type)
    {
    case NET_STATE_REQUEST_MEASURE:
        return parse_request_measure(packet, pkt_len);
    case NET_STATE_SET_FORCE_QUIT:
        return parse_set_force_quit(packet, pkt_len);
    case NET_STATE_SET_FREQUENCY:
        return parse_set_frequency(packet, pkt_len);
    default:
        return OFPERR_OFPBRC_BAD_SUBTYPE;
    }
}