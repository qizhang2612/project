#ifndef _REDIS_H_
#define _REDIS_H_

#include <hiredis/hiredis.h>
#include "utils.h"
#include "netstate-struct.h"


typedef struct WRControl
{
    int write;
    int read;
} WRControl;

extern volatile WRControl wr_ctl;

static inline void switch_wr_index()
{
    int tmp = wr_ctl.write;
    wr_ctl.write = wr_ctl.read;
    wr_ctl.read = tmp;
}

void update_value(redisContext *ctx, uint32_t key, uint32_t size, fiveTuple *five_tuple);
#endif // _REDIS_H_
