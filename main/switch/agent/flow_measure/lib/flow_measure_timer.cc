#include "flow_measure_timer.h"
#include <unistd.h>

uint64_t tsc_hz;

namespace
{

    class TscHzSetter
    {
    public:
        TscHzSetter()
        {
            uint64_t start = Timer::rdtsc();
            usleep(100000); // 0.1 sec
            tsc_hz = (uint64_t)((Timer::rdtsc() - start) * 10 / 100000000) * 100000000;
            LOG(INFO) << "tsc_hz: " << tsc_hz;
        }
    } _dummy;

}

FlowMeasureTimer::FlowMeasureTimer(uint64_t p, uint64_t i, uint64_t d, std::shared_ptr<EventList> event_list)
{
    this->event_list = event_list;
    thread_exit = false;
    write_index = 0;
    read_index = 1;

    measure_state.frequency.period = p * 1000ul;
    measure_state.frequency.interval = i;
    measure_state.frequency.duration = d * 1000ul;
    /*do not turn on flow measurement during initialization*/
    measure_state.force_quit = false;
    measure_state.open = false;
    uint64_t now = Timer::tsc_to_ms(Timer::rdtsc());

    /*give an offset*/
    measure_state.last_cycle = now - measure_state.frequency.interval;
    measure_state.last_time = measure_state.last_cycle;
    measure_state.begin_time = now - measure_state.frequency.duration;
}

void FlowMeasureTimer::MeasureStateControl()
{
    uint64_t now;
    uint64_t last;
    uint64_t interval;
    while (!thread_exit)
    {
        if (!event_list->Empty())
            event_list->ExtractAndHandle(&measure_state);
        now = Timer::tsc_to_ms(Timer::rdtsc());
        last = measure_state.last_time;
        interval = measure_state.frequency.interval;
        if (measure_state.open)
        {
            if (now >= measure_state.begin_time + measure_state.frequency.duration)
            {
                measure_state.last_cycle = now;
                measure_state.open = false;
                // LOG(INFO) << "stop measure";
            }
            if (now >= interval + last)
            {
                /*Disable instruction reordering by the compiler*/
                measure_state.last_time = now;
                SwitchWRIndex();
                barrier();
                readable = true;
                // LOG(INFO) << "new interval";
            }
        }
        /**
         * if reach the next flow measure period, open the flow measure and
         * set begin_time and last_time to now.
         * */
        else if (now >= measure_state.frequency.period + measure_state.last_cycle)
        {
            measure_state.begin_time = now;
            measure_state.last_time = now;
            measure_state.open = true;
            // LOG(INFO) << "start measure";
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(measure_state.frequency.interval / 10));
    }
}

void FlowMeasureTimer::StartTimer()
{
    LOG(INFO) << "start flow measure timer";
    timer_thread = std::thread(&FlowMeasureTimer::MeasureStateControl, this);
}

void FlowMeasureTimer::StopTimer()
{
    thread_exit = true;
}

void FlowMeasureTimer::Wait()
{
    timer_thread.join();
}