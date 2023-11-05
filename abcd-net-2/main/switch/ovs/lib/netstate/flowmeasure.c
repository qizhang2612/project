#include "flowmeasure.h"
#include "openvswitch/vlog.h"
#include <unistd.h>
#include <config.h>
#include <rte_byteorder.h>
#include <rte_lcore.h>
#include <rte_time.h>
#include <rte_timer.h>
VLOG_DEFINE_THIS_MODULE(flowmeasure);

redisContext *ctx[MAX_CPU_NUM] =
    {NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL};
volatile measureState measure_state;
rte_spinlock_t lock;
rte_spinlock_t create_thread_lock;
volatile bool rd_flag = false;
bool read_thread_exit = false;

static void load_conf()
{
    config_t cfg;
    int count;

    config_init(&cfg);
    if (!config_read_file(&cfg, netstate_config_file))
    {
        VLOG_ERR("INIT NETSTAT ERRORE!");
        config_destroy(&cfg);
        abort();
    }

    /*setting measeurement frequency*/
    config_setting_t *frequency = config_lookup(&cfg, "flow_measure.frequency");
    if (unlikely(frequency == NULL))
    {
        VLOG_ERR("INIT FLOW MEASURE ERROR!");
        abort();
    }
    count = config_setting_length(frequency);
    ovs_assert(count == 3);
    int period, interval, duration;
    if (!(config_setting_lookup_int(frequency, "period", &period) &&
          config_setting_lookup_int(frequency, "interval", &interval) &&
          config_setting_lookup_int(frequency, "duration", &duration)))
        abort();
    VLOG_INFO("peroid:%d interval:%d duration:%d", period, interval, duration);
    measure_state.frequency.period = period * USEC_PER_MSEC;
    measure_state.frequency.interval = interval * USEC_PER_MSEC;
    measure_state.frequency.duration = duration * USEC_PER_MSEC;
    /*do not turn on flow measurement during initialization*/
    uint64_t now = tsc_to_us(rdtsc());
    measure_state.force_quit = false;
    measure_state.open = false;
    /*give an offset*/
    measure_state.last_cycle = now - measure_state.frequency.interval;
    measure_state.last_time = measure_state.last_cycle;
    measure_state.begin_time = now - measure_state.frequency.duration;

    const char *ip;
    int port;
    /*setting redis address and port*/
    config_setting_t *redis = config_lookup(&cfg, "flow_measure.redis_server");
    if (unlikely(redis == NULL))
    {
        VLOG_ERR("INIT REDIS ADDRESS ERROR!");
        abort();
    }
    count = config_setting_length(redis);
    ovs_assert(count == 2);
    if (!(config_setting_lookup_string(redis, "ip", &ip) &&
          config_setting_lookup_int(redis, "port", &port)))
        abort();
    VLOG_INFO("redis ip:%s port:%d", ip, port);
    redis_server.ip = strdup(ip);
    redis_server.port = port;

    /*setting receiver address and port*/
    config_setting_t *recv = config_lookup(&cfg, "flow_measure.receive_server");
    if (unlikely(recv == NULL))
    {
        VLOG_ERR("INIT RECEIVER SERVER ERROR!");
        abort();
    }
    count = config_setting_length(recv);
    ovs_assert(count == 2);
    if (!(config_setting_lookup_string(recv, "ip", &ip) &&
          config_setting_lookup_int(recv, "port", &port)))
        abort();
    VLOG_INFO("receive ip:%s port:%d", ip, port);
    measure_state.recv_server.sin_family = AF_INET;
    measure_state.recv_server.sin_port = htons(port);
    measure_state.recv_server.sin_addr.s_addr = inet_addr(ip);
    recv_port = port;
    recv_ip = ntohl(inet_addr(ip));

    config_destroy(&cfg);
}

static void set_redis_connection()
{
    for (int i = 0; i < MAX_CPU_NUM; i++)
    {
        ctx[i] = redisConnect(redis_server.ip, redis_server.port);
        if (ctx[i] != NULL && ctx[i]->err)
        {
            VLOG_ERR("Error establishing redis connection");
            abort();
        }
    }
    // clean history data in redis when init
    redisReply *clean = (redisReply *)redisCommand(ctx[0], "FLUSHALL");
    freeReplyObject(clean);
    clean = (redisReply *)redisCommand(ctx[0], "SELECT 1");
    freeReplyObject(clean);
    clean = (redisReply *)redisCommand(ctx[0], "FLUSHALL");
    freeReplyObject(clean);
    clean = (redisReply *)redisCommand(ctx[0], "SELECT 0");
    freeReplyObject(clean);
}

void init_flow_measure()
{
    /* load conf must be the first step */
    load_conf();
    set_redis_connection();
    init_tsc_hz();
    init_netstate_events(&event_list);
    rte_spinlock_init(&lock);
    rte_spinlock_init(&create_thread_lock);
}

int send_to_controller(const void *buffer, size_t size, int client_fd)
{
    return send(client_fd, buffer, size, 0);
}

static int send_end_msg(int client_fd)
{
    const char *buffer = "end";
    return send_to_controller(buffer, strlen(buffer), client_fd);
}

void parse_five_tuple(fiveTuple *five_tuple, const struct dp_packet *packet)
{
    if (packet == NULL)
        return;
    if (unlikely(!dp_packet_is_eth(packet)))
        return;
    struct eth_header *l2 = dp_packet_eth(packet);
    if (unlikely(rte_be_to_cpu_16(l2->eth_type) != ETH_TYPE_IP))
        return;
    struct ip_header *l3 = dp_packet_l3(packet);
    five_tuple->src_ip = rte_be_to_cpu_32(get_16aligned_be32(&l3->ip_src));
    five_tuple->dst_ip = rte_be_to_cpu_32(get_16aligned_be32(&l3->ip_dst));
    five_tuple->protocol = l3->ip_proto;

    void *l4 = dp_packet_l4(packet);
    if (l3->ip_proto == IPPROTO_UDP)
    {
        five_tuple->src_port = rte_be_to_cpu_16(((struct udp_header *)l4)->udp_src);
        five_tuple->dst_port = rte_be_to_cpu_16(((struct udp_header *)l4)->udp_dst);
    }
    else if (l3->ip_proto == IPPROTO_TCP)
    {
        five_tuple->src_port = rte_be_to_cpu_16(((struct tcp_header *)l4)->tcp_src);
        five_tuple->dst_port = rte_be_to_cpu_16(((struct tcp_header *)l4)->tcp_dst);
    }
}

void *read_measure_data(void *arg)
{
    redisContext *read_ctx = redisConnect(redis_server.ip, redis_server.port);
    if (read_ctx != NULL && read_ctx->err)
    {
        VLOG_INFO("Failed to establish connection to redis \
                    when creating read measure data thread");
        return NULL;
    }

    int client_fd;
    char buffer[MAX_BUFFER_SIZE];
    int pos;
    int flow_count;
    int need;
    redisReply *key_query;
    redisReply *val_query;
    redisReply *ctrl_query;
    need = sizeof(uint32_t) * 2 + sizeof(uint16_t) * 2 + sizeof(uint8_t) + sizeof(uint32_t) * 2;
    VLOG_INFO("create read thread");
    usleep(5000000);
    while (!read_thread_exit)
    {
        if (likely(rd_flag == false))
        {
            if (measure_state.open)
                usleep(measure_state.frequency.interval / 10);
            else
                usleep(measure_state.frequency.period / 10);
            continue;
        }
        /*connect with flow measure server*/
        client_fd = socket(AF_INET, SOCK_STREAM, 0);
        int re = connect(client_fd, (struct sockaddr *)&measure_state.recv_server, sizeof(measure_state.recv_server));
        if (unlikely(re < 0))
        {
            VLOG_INFO("failed to connect with flowmeasure server");
            return NULL;
        }

        /*clear buffer and reset data position*/
        memset(buffer, 0, MAX_BUFFER_SIZE);
        pos = MEASURE_DATA_BEGIN;
        flow_count = 0;

        /**
         * 1. switch to read table
         * 2. query flow num
         * 3. read flow data from redis sequentially
         */
        key_query = (redisReply *)redisCommand(read_ctx, "SELECT %d", wr_ctl.read);
        if (unlikely(key_query == NULL))
        {
            redisReconnect(read_ctx);
            freeReplyObject(key_query);
            key_query = (redisReply *)redisCommand(read_ctx, "SELECT %d", wr_ctl.read);
        }
        freeReplyObject(key_query);
        key_query = (redisReply *)redisCommand(read_ctx, "KEYS *");
        for (int i = 0; i < key_query->elements; i++)
        {
            val_query = (redisReply *)redisCommand(read_ctx, "HVALS %s", key_query->element[i]->str);
            if (unlikely(val_query->elements != REDIS_VAL_NUM))
            {
                freeReplyObject(val_query);
                continue;
            }
            if (unlikely(atoi(val_query->element[FLOW_SIZE_OFFSET]->str) == 0))
            {
                ctrl_query = (redisReply *)redisCommand(read_ctx, "DEL %s", key_query->element[i]->str);
                freeReplyObject(ctrl_query);
                continue;
            }
            if (unlikely(MAX_BUFFER_SIZE < pos + need))
            {
                memcpy(buffer, &flow_count, sizeof(uint32_t));
                int re = send_to_controller(buffer, pos, client_fd);
                if (unlikely(re < 0))
                    VLOG_ERR("send measure data to controller failed!");
                memset(buffer, 0, MAX_BUFFER_SIZE);
                pos = MEASURE_DATA_BEGIN;
                flow_count = 0;
            }
            for (int j = 0; j < val_query->elements; j++)
            {
                uint32_t re = atoi(val_query->element[j]->str);
                memcpy(buffer + pos, &re, copy_len[j]);
                pos += copy_len[j];
            }
            flow_count++;
            freeReplyObject(val_query);
            ctrl_query = redisCommand(read_ctx, "HMSET %s size %d num %d", key_query->element[i]->str, 0, 0);
            freeReplyObject(ctrl_query);
        }
        freeReplyObject(key_query);
        if (pos > MEASURE_DATA_BEGIN)
        {
            memcpy(buffer, &flow_count, sizeof(uint32_t));
            if (send_to_controller(buffer, pos, client_fd) < 0)
                VLOG_ERR("send measure data to controller failed!");
        }

        // re = send_end_msg(client_fd);
        // if (unlikely(re < 0))
        //     VLOG_ERR("send end msg failed!");
        rd_flag = false;
        close(client_fd);
    }

    return NULL;
}

void read_measure_exit(pthread_t pid)
{
    read_thread_exit = true;
    pthread_join(pid, NULL);
}

void measure_state_control()
{
    uint64_t now;
    uint64_t last;
    uint64_t interval;
    /**
     * spinlock, ensure the action of switching write and read index
     * occurs only once without blocking.Also, ensure the read thread
     * will be created only once without giving back lock.
     **/
    if (unlikely(rte_spinlock_trylock(&create_thread_lock)))
    {
        pthread_t read_pid;
        pthread_create(&read_pid, NULL, read_measure_data, NULL);
        VLOG_INFO("create read thread, thread id %d", read_pid);
    }
    if (rte_spinlock_trylock(&lock))
    {
        /*handle instruction from controller*/
        if (unlikely(event_list.event_num != 0))
        {
            struct event *e = extract_event(&event_list);
            e->handler(&measure_state, e->data);
        }
        now = tsc_to_us(rdtsc());
        last = measure_state.last_time;
        interval = measure_state.frequency.interval;
        if (measure_state.open)
        {
            if (unlikely(now >= measure_state.begin_time + measure_state.frequency.duration))
            {
                measure_state.last_cycle = now;
                measure_state.open = false;
            }
            if (unlikely(now >= interval + last))
            {
                /*Disable instruction reordering by the compiler*/
                measure_state.last_time = now;
                switch_wr_index();
                barrier();
                rd_flag = 1;
            }
        }
        /**
         * if reach the next flow measure period, open the switch and
         * set begin_time and last_time to now.
         * */
        else if (unlikely(now >= measure_state.frequency.period + measure_state.last_cycle))
        {
            measure_state.begin_time = now;
            measure_state.last_time = now;
            measure_state.open = true;
        }
        rte_spinlock_unlock(&lock);
    }
}

void update_measure_data(const struct dp_packet *packet, uint32_t hash)
{
    if (unlikely(measure_state.open == false || measure_state.force_quit == true))
        return;

    int cpu_id;
    uint32_t size;
    fiveTuple five_tuple;
    cpu_id = rte_lcore_id();
    if (unlikely(cpu_id == LCORE_ID_ANY))
    {
        if (getcpu(&cpu_id, NULL) < 0)
        {
            cpu_id = 0;
            VLOG_WARN("get cpu id error");
        }
    }
    size = dp_packet_size(packet);
    parse_five_tuple(&five_tuple, packet);
    update_value(ctx[cpu_id], hash, size, &five_tuple);
}