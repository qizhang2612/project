#include "redis.h"
#include "openvswitch/vlog.h"
#include <config.h>
VLOG_DEFINE_THIS_MODULE(redis);

extern volatile WRControl wr_ctl = {.write = 0, .read = 1};

void update_value(redisContext *ctx, uint32_t key, uint32_t size, fiveTuple *five_tuple)
{
    redisReply *reply;
    reply = (redisReply *)redisCommand(ctx, "SELECT %d", wr_ctl.write);
    if (unlikely(reply == NULL))
        redisReconnect(ctx);
    freeReplyObject(reply);
    reply = (redisReply *)redisCommand(ctx, "EXISTS %u", key);
    if (unlikely(reply->integer == 0))
    {
        freeReplyObject(reply);
        reply = (redisReply *)redisCommand(
            ctx, "HMSET %u src_ip %u dst_ip %u src_port %u dst_port %u protocol %u size %u num %u", key,
            five_tuple->src_ip, five_tuple->dst_ip, five_tuple->src_port, five_tuple->dst_port, five_tuple->protocol, size, 1);
    }
    else
    {
        freeReplyObject(reply);
        reply = (redisReply *)redisCommand(ctx, "HINCRBY %u size %u", key, size);
        freeReplyObject(reply);
        reply = (redisReply *)redisCommand(ctx, "HINCRBY %u num %u", key, 1);
    }
    freeReplyObject(reply);
}