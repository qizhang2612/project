#ifndef _FLOWMEASURE_H_
#define _FLOWMEASURE_H_
#include "dp-packet.h"
#include "packets.h"
#include "redis.h"
#include "utils.h"
#include <libconfig.h>
#include <sched.h>
#include <rte_spinlock.h>
#include "netstate-struct.h"

#define REDIS_VAL_NUM 7
#define FLOW_SIZE_OFFSET 5
#define MAX_BUFFER_SIZE 4096

/**
 * When sending a packet, the first four bytes of the buffer 
 * are used to identify how many flows are sent this time
 * So the measurement data starts at an offset of four bytes
 */
#define MEASURE_DATA_BEGIN 4

static int copy_len[REDIS_VAL_NUM] = {4, 4, 2, 2, 1, 4, 4};
static redisServer redis_server;
static uint32_t recv_ip;
static uint32_t recv_port;

extern rte_spinlock_t lock;
extern rte_spinlock_t create_thread_lock;
extern volatile bool rd_flag;
extern bool read_thread_exit;
extern redisContext *ctx[MAX_CPU_NUM];
extern volatile measureState measure_state;

/**
 * @brief
 * read the configuration file, initialize variables
 */
void init_flow_measure();

/**
 * @brief
 * send flow measure data to server, return 0 if send
 * @param buffer
 * @param size
 * @param client_fd
 * @return int
 */
int send_to_controller(const void *buffer, size_t size, int client_fd);

/**
 * @brief
 * parse five tuple from a packet who's l4 type is udp or tcp,the user
 * need to externally ensure that incoming packet's l3 type is IPv4.
 * @param five_tuple pointer to a five-tuple struct to be written
 * @param packet pointer to a IPv4 packet
 */
void parse_five_tuple(fiveTuple *five_tuple, const struct dp_packet *packet);

/**
 * @brief
 * this function will be executed as a child thread to read flow measurement
 * data from redis and send data to the controller deployed on the remote host.
 * @return void*
 */
void *read_measure_data(void *arg);
void read_measure_exit(pthread_t pid);

/**
 * @brief
 * Due to the existence of timing measurement, each time a packet is received,the
 * measurement status should be detected first, and the time variable in measure_stat
 * should be set. Then update one flow's measure data the packet belongs to, only process
 * IPv4 packets.
 * @param packet pointer to a packet
 * @param hash packet's hash calculated by open vswitch
 */
void measure_state_control();
void update_measure_data(const struct dp_packet *packet, uint32_t hash);

#endif // _FLOWMEASURE_H_

/**
 * 编译前记得export CFLAGS=-mavx
 *
 */