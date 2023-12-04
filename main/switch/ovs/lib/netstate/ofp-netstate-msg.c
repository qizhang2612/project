#include "ofp-netstate-msg.h"
#include "openvswitch/vlog.h"
VLOG_DEFINE_THIS_MODULE(ofp_netstate_msg);

void set_force_quit_handler(void *dst, void *msg)
{
    measureState *state = (measureState *)dst;
    setForceQuitMsg *msg_ = (setForceQuitMsg *)msg;
    state->force_quit = msg_->force_quit == 1 ? true : false;
    free(msg);
}

void request_measure_handler(void *dst, void *msg)
{
    measureState *state = (measureState *)dst;
    uint64_t now = tsc_to_us(rdtsc());
    state->last_cycle = now - state->frequency.period;
    state->last_time = now;
    state->begin_time = now;
    state->open = true;
    if (msg != NULL)
        free(msg);
}

void set_frequency_handler(void *dst, void *msg)
{
    measureState *state = (measureState *)dst;
    setFrequencyMsg *msg_ = (setFrequencyMsg *)msg;
    state->frequency.period = msg_->period * USEC_PER_MSEC;
    state->frequency.interval = msg_->interval * USEC_PER_MSEC;
    state->frequency.duration = msg_->duration * USEC_PER_MSEC;
    free(msg);
}

enum ofperr parse_set_force_quit(uint8_t *packet, uint32_t pkt_len)
{
    VLOG_INFO("request set force quit msg");
    if (pkt_len < OFP_PAYLOAD_OFFSET + 1)
    {
        VLOG_ERR("bad length when parse set force quit msg");
        return OFPERR_OFPBAC_BAD_LEN;
    }
    setForceQuitMsg *force_quit = (setForceQuitMsg *)malloc(sizeof(setForceQuitMsg));
    force_quit->force_quit = *(packet + OFP_PAYLOAD_OFFSET);
    VLOG_INFO("quit state:%d", force_quit->force_quit);
    struct event *e = (struct event *)malloc(sizeof(struct event));
    e->data = force_quit;
    e->handler = set_force_quit_handler;
    add_new_event(&event_list, e);
    return 0;
}

enum ofperr parse_request_measure(uint8_t *packet, uint32_t pkt_len)
{
    VLOG_INFO("receive request flow measure msg");
    struct event *e = (struct event *)malloc(sizeof(struct event));
    e->data = NULL;
    e->handler = request_measure_handler;
    add_new_event(&event_list, e);
    return 0;
}

enum ofperr parse_set_frequency(uint8_t *packet, uint32_t pkt_len)
{
    VLOG_INFO("receive set frequency msg");
    if (pkt_len < OFP_PAYLOAD_OFFSET + sizeof(measureFrequency))
    {
        VLOG_ERR("bad length when parse set frequency msg");
        return OFPERR_OFPBAC_BAD_LEN;
    }
    measureFrequency *frequency = (measureFrequency *)malloc(sizeof(measureFrequency));
    int offset = OFP_PAYLOAD_OFFSET;
    frequency->period = rte_be_to_cpu_64(*(uint64_t *)(packet + offset));
    offset += sizeof(uint64_t);
    frequency->interval = rte_be_to_cpu_64(*(uint64_t *)(packet + offset));
    offset += sizeof(uint64_t);
    frequency->duration = rte_be_to_cpu_64(*(uint64_t *)(packet + offset));
    VLOG_INFO("period:%llu  interval:%llu  duration:%llu", frequency->period, frequency->interval, frequency->duration);

    struct event *e = (struct event *)malloc(sizeof(struct event));
    e->data = frequency;
    e->handler = set_frequency_handler;
    add_new_event(&event_list, e);
    return 0;
}