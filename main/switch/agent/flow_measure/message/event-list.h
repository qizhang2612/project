#ifndef _EVENT_LIST_H_
#define _EVENT_LIST_H_
#include <cstdint>
#include <queue>
#include <memory>
#include <pthread.h>

struct MeasureState;

class Event
{
private:
    using Handler_t = void (*)(MeasureState *user_data, void *msg);
    void *msg;
    Handler_t handler;

public:
    Event() = default;
    Event(void *msg, Handler_t handler)
    {
        this->msg = msg;
        this->handler = handler;
    }

    void HandleEvent(MeasureState *user_data)
    {
        handler(user_data, msg);
    }
};

class EventList
{
private:
    pthread_spinlock_t lock;
    std::queue<Event> events;

public:
    EventList()
    {
        pthread_spin_init(&lock, PTHREAD_PROCESS_SHARED);
    }
    bool Empty()
    {
        return events.empty();
    }
    void ExtractAndHandle(MeasureState *data);
    void AddEvent(Event &event);
};

#endif // _EVENT_LIST_H_