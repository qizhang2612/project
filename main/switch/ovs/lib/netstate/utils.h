#ifndef _UTILS_H_
#define _UTILS_H_

#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <inttypes.h>
#include <sys/time.h>
#include <rte_time.h>
#include <rte_cycles.h>

#define MAX_CPU_NUM 16
#define USEC_PER_MSEC 1000
#define likely(x) __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
#define barrier() asm volatile("" \
                               :  \
                               :  \
                               : "memory")
extern uint64_t tsc_hz;

void init_tsc_hz();

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

#endif // _UTILS_H_