#ifndef _NETSTATE_STRUCT_H_
#define _NETSTATE_STRUCT_H_
#include <arpa/inet.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <rte_spinlock.h>

typedef struct measureFrequency
{
    /*microsecond*/
    uint64_t period;   // how often to start a new measurement cycle
    uint64_t interval; // time per measurement segment
    uint64_t duration; // one measurement cycle duration
} measureFrequency;

typedef struct measureState
{
    bool force_quit;     // don't do any flow measure if true,set by controller
    bool open;           // switch to control the measurement
    uint64_t begin_time; // begin time of this measurement cycle
    uint64_t last_time;  // end time of last measurement segment
    uint64_t last_cycle; // end time of last period
    measureFrequency frequency;
    struct sockaddr_in recv_server; // server that receives measurement data
} measureState;

typedef struct fiveTuple
{
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t protocol; // 0: OTHER, 6: TCP, 17: UDP
} fiveTuple;

typedef struct redisServer
{
    const char *ip;
    int port;
} redisServer;

typedef void (*handler_t)(void *, void *);
struct event
{
    struct event *next;
    void *data;
    handler_t handler;
};
typedef struct netstateEventList
{
    struct event *head;
    struct event *tail; // point to the last node
    int event_num;
    rte_spinlock_t lock;
} netstateEventList;

extern netstateEventList event_list;
static const char *netstate_config_file = "/dev/shm/netstate.cfg";

void init_netstate_events(netstateEventList *events);
void add_new_event(netstateEventList *events, struct event *e);
struct event *extract_event(netstateEventList *events);

#endif // _NETSTATE_STRUCT_H_