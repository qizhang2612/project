#include "netstate-struct.h"

netstateEventList event_list;
void init_netstate_events(netstateEventList *events)
{
    events->event_num = 0;
    rte_spinlock_init(&(events->lock));
    events->head = (struct event *)malloc(sizeof(struct event));
    events->tail = events->head;
    events->head->next = NULL;
}

void add_new_event(netstateEventList *events, struct event *e)
{
    rte_spinlock_lock(&(events->lock));
    events->event_num++;
    events->tail->next = e;
    e->next = NULL;
    events->tail = e;
    rte_spinlock_unlock(&(events->lock));
}

struct event *extract_event(netstateEventList *events)
{
    struct event *e;
    if (likely(rte_spinlock_trylock(&(events->lock))))
    {
        if (events->event_num <= 0)
            e = NULL;
        else
        {
            events->event_num--;
            if (events->event_num == 0)
                events->tail = events->head;
            e = events->head->next;
            events->head->next = e->next;
            e->next = NULL;
        }
        rte_spinlock_unlock(&(events->lock));
    }

    return e;
}