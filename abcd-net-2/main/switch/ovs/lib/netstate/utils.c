#include "utils.h"
#include "openvswitch/vlog.h"
#include <unistd.h>
VLOG_DEFINE_THIS_MODULE(utils);
uint64_t tsc_hz;

void init_tsc_hz()
{
    uint64_t start = rdtsc();
    usleep(100000); // 0.1 sec
    tsc_hz = (uint64_t)((rdtsc() - start) * 10 / 100000000) * 100000000;
    VLOG_INFO("tsc_hz:%llu", tsc_hz);
}