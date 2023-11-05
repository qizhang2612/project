#ifndef _FLOW_MEASURE_TIMER_H_
#define _FLOW_MEASURE_TIMER_H_
#include <cstdint>
#include <ctime>
#include <cstdlib>
#include <sys/time.h>
#include <glog/logging.h>
#include <memory>
#include <thread>
#include "../message/ants-msg.h"

#define barrier() asm volatile("" \
                               :  \
                               :  \
                               : "memory")

extern uint64_t tsc_hz;

struct MeasureFrequency
{
    /*millisecond*/
    uint64_t interval; // time per measurement segment
    uint64_t duration; // one measurement cycle duration
    uint64_t period;   // how often to start a new measurement cycle
};

struct MeasureState
{
    bool force_quit;     // don't do any flow measure if true,set by controller
    bool open;           // switch to control the measurement
    uint64_t begin_time; // begin time of this measurement cycle
    uint64_t last_time;  // end time of last measurement segment
    uint64_t last_cycle; // end time of last period
    MeasureFrequency frequency;
};

class Timer
{
public:
    static const uint64_t MSEC_PER_SEC = 1000;
    static inline uint64_t rdtsc(void)
    {
        uint32_t hi, lo;
        __asm__ __volatile__("rdtsc"
                             : "=a"(lo), "=d"(hi));
        return (uint64_t)lo | ((uint64_t)hi << 32);
    }
    static inline uint64_t tsc_to_ns(uint64_t cycles)
    {
        return cycles * 1000000000.0 / tsc_hz;
    }
    static inline double tsc_to_us(uint64_t cycles)
    {
        return cycles * 1000000.0 / tsc_hz;
    }
    static inline double tsc_to_ms(uint64_t cycles)
    {
        return cycles * 1000.0 / tsc_hz;
    }

    /* Return current time in seconds since the Epoch.
     * This is consistent with Python's time.time() */
    static inline double get_epoch_time()
    {
        struct timeval tv;
        gettimeofday(&tv, nullptr);
        return tv.tv_sec + tv.tv_usec / 1e6;
    }

    /* CPU time (in seconds) spent by the current thread.
     * Use it only relatively. */
    static inline double get_cpu_time()
    {
        struct timespec ts;
        if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts) == 0)
            return ts.tv_sec + ts.tv_nsec / 1e9;
        else
            return get_epoch_time();
    }
};

class FlowMeasureControl
{
public:
    virtual bool Paused() = 0;
    virtual bool Exited() = 0;
    virtual bool Readable() = 0;
    virtual void SetUnReadable() = 0;
    virtual int GetCurrentReadIndex() = 0;
    virtual int GetCurrentWriteIndex() = 0;
    virtual int Interval() = 0;
    virtual int Period() = 0;
    virtual int Duration() = 0;
    virtual ~FlowMeasureControl() = default;
};

class FlowMeasureTimer : public FlowMeasureControl
{
private:
    MeasureState measure_state;
    std::thread timer_thread;
    std::shared_ptr<EventList> event_list;
    bool thread_exit;
    bool readable;
    int write_index;
    int read_index;

    void SwitchWRIndex()
    {
        write_index ^= 1;
        read_index ^= 1;
    }

public:
    virtual ~FlowMeasureTimer() = default;
    /**
     * @brief Construct a new Flow Measure Timer object
     *
     * @param p period, s
     * @param i interval, ms
     * @param d duration, s
     * @param event_list
     */
    FlowMeasureTimer(uint64_t p, uint64_t i, uint64_t d, std::shared_ptr<EventList> event_list);
    bool Paused() override
    {
        return measure_state.open == false;
    }

    bool Exited() override
    {
        return measure_state.force_quit == true;
    }

    bool Readable() override
    {
        return readable;
    }

    void SetUnReadable() override
    {
        readable = false;
    }

    int GetCurrentReadIndex() override
    {
        return read_index;
    }

    int GetCurrentWriteIndex() override
    {
        return write_index;
    }
    int Interval() override
    {
        return measure_state.frequency.interval;
    }
    int Period() override
    {
        return measure_state.frequency.period;
    }
    int Duration() override
    {
        return measure_state.frequency.duration;
    }

    void MeasureStateControl();
    void StartTimer();
    void StopTimer();
    void Wait();
};

#endif // _FLOW_MEASURE_TIMER_H_