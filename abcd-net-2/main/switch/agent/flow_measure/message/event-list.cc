#include "event-list.h"
#include "../lib/flow_measure_timer.h"

void EventList::ExtractAndHandle(MeasureState *data)
{
    if (!events.empty() && pthread_spin_trylock(&lock) == 0)
    {
        auto event = events.front();
        event.HandleEvent(data);
        events.pop();
        pthread_spin_unlock(&lock);
    }
}

void EventList::AddEvent(Event &event)
{
    pthread_spin_lock(&lock);
    LOG(INFO) << "add new event";
    events.push(event);
    pthread_spin_unlock(&lock);
}