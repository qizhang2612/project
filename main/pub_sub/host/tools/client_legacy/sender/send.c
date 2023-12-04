#include <stdio.h>
#include <getopt.h>
#include "../lib/json/cJSON.h"
#include "unistd.h"
#include "sys/socket.h"
#include "netinet/in.h"
#include "arpa/inet.h"
#include "string.h"
#include "stdlib.h"

#define MAX_BUF_LEN 512
#define MAX_ADDR_LEN 50
#define DATA_PORT 8889
#define RECV_PORT 9000

int create_data_connection() {
    // create data socket.
    int fd_data = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr_data;
    memset(&addr_data, 0, sizeof(addr_data));
    addr_data.sin_family = AF_INET;
    addr_data.sin_port = htons(DATA_PORT);
    addr_data.sin_addr.s_addr = inet_addr("127.0.0.1");

    int ret = connect(fd_data, (struct sockaddr *) &addr_data, sizeof(addr_data));
    if (ret == -1) {
        printf("data service connect error.\n");
        exit(1);
    }

    return fd_data;
}


// Send message to the topics subscribed
//
// Args:
//  data: the message host want to send
//  addr_nums: the number of the address
//  addresses: a array of string representing topic's IP addresses
void send_to_sub(char *data, int addr_nums, char (*addresses)[MAX_ADDR_LEN] ){
    for(int i = 0;i < addr_nums; i++) {
        struct sockaddr_in addr_recv;
        int len = sizeof(addr_recv);
        int fd = socket(AF_INET, SOCK_DGRAM, 0);
        addr_recv.sin_family = AF_INET;
        addr_recv.sin_addr.s_addr = inet_addr(addresses[i]);
        addr_recv.sin_port = htons(RECV_PORT);
        bind(fd, (struct sockaddr *) &addr_recv, len);

        sendto(fd, data, strlen(data), 0, (struct sockaddr *) &addr_recv, len);
        printf("send msg to %s\n", addresses[i]);
        close(fd);
    }

    return;
}

// Send query message to local database to get
// all the subscribed topic's IP address
//
// Args:
//  data: The string of the message
//  addresses: A array to store the subscribed topic's IP address
//             from the database
int get_sub_addresses(char *data, char (*addresses)[MAX_ADDR_LEN]) {
    cJSON *cjson_data = (cJSON *) cJSON_Parse(data);
    cJSON *cjson_data_area = (cJSON *) cJSON_GetObjectItem(cjson_data, "area");
    char *area = cjson_data_area->valuestring;

    int addr_nums = 0;
    char buf[MAX_BUF_LEN] = {0};
    strcpy(buf, "get sub");

    // Connect to the database, and
    // receive the database's checking result
    int fd_data = create_data_connection();
    send(fd_data, buf, strlen(buf), 0);

    bzero(buf, MAX_BUF_LEN);
    recv(fd_data, buf, MAX_BUF_LEN, 0);

    cJSON *cjson_result = (cJSON *) cJSON_Parse(buf);
    if (cjson_result == NULL) {
        printf("reply from storage service parse failed, "
               "check connection and data format!!!\n");
        return 0;
    }

    // Get the subscribed topic's IP addresses
    cJSON *cjson_status = (cJSON *) cJSON_GetObjectItem(cjson_result, "status");
    cJSON *cjson_msg = (cJSON *) cJSON_GetObjectItem(cjson_result, "msg");
    int sub_array_size = cJSON_GetArraySize(cjson_msg);
    for(int i = 0; i < sub_array_size; i++)
    {
        cJSON *cjson_sub_item = cJSON_GetArrayItem(cjson_msg, i);

        cJSON *cjson_ip = cJSON_GetArrayItem(cjson_sub_item, 0);
        cJSON *cjson_area = cJSON_GetArrayItem(cjson_sub_item, 1);
        if (strcmp(area, cjson_area->valuestring) == 0) {
            strcpy(addresses[addr_nums++], cjson_ip->valuestring);
        }
    }

    close(fd_data);
    return addr_nums;
}

// Send message to the multicast address, to
// make every subscribe receive the message
//
// Args:
//  data: the message topic want to send
//  address: the multicast address representing the topic
void send_to_pub(char *data, char *address){
    // Build the socket
    struct sockaddr_in addr_recv;
    int len = sizeof(addr_recv);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = inet_addr(address);
    addr_recv.sin_port = htons(RECV_PORT);
    bind(fd, (struct sockaddr *) &addr_recv, len);

    sendto(fd, data, strlen(data), 0, (struct sockaddr *) &addr_recv, len);
    printf("send msg to %s\n", address);

    close(fd);
    return;
}

// Get the topic's multicast address from the
// local database
//
// Args:
//  address: the buffer to store the requesting database's
//           checking result
void get_group_address(char *address) {
    char buf[MAX_BUF_LEN] = {0};
    strcpy(buf, "get pub");

    int fd_data = create_data_connection();
    send(fd_data, buf, strlen(buf), 0);

    bzero(buf, MAX_BUF_LEN);
    recv(fd_data, buf, MAX_BUF_LEN, 0);

    cJSON *cjson_result = (cJSON *) cJSON_Parse(buf);
    if (cjson_result == NULL) {
        printf("reply from storage service parse failed, "
               "check connection and data format!!!\n");
        return;
    }
    cJSON *cjson_status = (cJSON *) cJSON_GetObjectItem(cjson_result, "status");
    cJSON *cjson_msg = (cJSON *) cJSON_GetObjectItem(cjson_result, "msg");

    strcpy(address, cjson_msg->valuestring);
    close(fd_data);
}

// Send the message
//
// Args:
//  buf: A string representing the message host wants to send
//  positive: If it is true, we will find all the topic's the host
//            subscribed, and send the message to them. If it is false,
//            we will send the message to the subscribers, which subscribing
//            the host's topic by a multicast address.
void send_data(char *buf, int positive) {
    if (!positive) {
        char address[MAX_ADDR_LEN];
        get_group_address(address);
        send_to_pub(buf, address);
    } else {
        char addresses[MAX_ADDR_LEN][MAX_ADDR_LEN];
        int addr_nums = get_sub_addresses(buf, addresses);
        send_to_sub(buf, addr_nums, addresses);
    }
}

// Generate some random message
//
// Args:
//  buf: A buffer to store message string
void generate_notification_data(char *buf) {
    sleep(2);
    int area = rand() % 2 + 1;
    if (area == 1) {
        bzero(buf, MAX_BUF_LEN);
        strcpy(buf, "{\"area\": \"A\", \"location\": \"(longitude1, latitude1, altitude1)\"}");
    } else {
        bzero(buf, MAX_BUF_LEN);
        strcpy(buf, "{\"area\": \"B\", \"location\": \"(longitude2, latitude2, altitude2)\"}");
    }
    printf("\nmsg: %s\n", buf);
}

// Generate some random message
//
// Args:
//  buf: A buffer to store message string
void generate_command_data(char *buf) {
    sleep(2);
    int area = rand() % 2 + 1;
    if (area == 1) {
        bzero(buf, MAX_BUF_LEN);
        strcpy(buf, "{\"area\": \"A\", \"location\": \"(longitude1, latitude1, altitude1)\"}");
    } else {
        bzero(buf, MAX_BUF_LEN);
        strcpy(buf, "{\"area\": \"B\", \"location\": \"(longitude2, latitude2, altitude2)\"}");
    }
    printf("\nmsg: %s\n", buf);
}

// Get the message, which should be sent later
//
// Args:
//  buf: A buffer to store message string
//  simulate: If it is true, we generate some random message.
//            If it is false, we need the user input some data.
//  positive: Now it is no use, because the two functions work almost
//            the same. But we maybe distinguish the two functions later.
void get_data(char *buf, int simulate, int positive) {
    if (simulate) {
        if (positive) {
            generate_command_data(buf);
        } else {
            generate_notification_data(buf);
        }
    } else {
        printf("msg >> ");
        fflush(stdout);
        fgets(buf, MAX_BUF_LEN, stdin);
    }
}

// If the user input the wrong string
// we will give some guides
//
// Args:
//  stream: The place where we put the help string.
//  exit_code: After we give the guides, we will exit the program with a exit code
void print_usage(FILE *stream, int exit_code) {
    fprintf(stream, "Usage: sender options\n ");
    fprintf(stream,
            "-h --help\t\t null, to display this usage.\n"
            " -s --simulate\t\t null, send simulate data periodically.\n"
            " -p --positive\t\t null, host send cmd data positively.\n");

    exit(exit_code);
}

int main(int argc, char *argv[]) {
    const char *const short_options = "shp";
    const struct option long_options[] = {
            {"simulate", 0, NULL, 's'},
            {"positive", 0, NULL, 'p'},
            {"help",     0, NULL, 'h'},
            {NULL,       0, NULL, 0}
    };

    int simulate = 0;
    int positive = 0;
    int next_option = 1;

    // Get a executable command from user
    // or exit the program if the user give
    // the wrong input
    do {
        next_option = getopt_long(argc, argv, short_options, long_options, NULL);

        switch (next_option) {
            case 'h':
                print_usage(stdout, 0);
                break;
            case 's':
                simulate = 1;
                break;
            case 'p':
                positive = 1;
            case -1: // done with options.
                break;
            default: // something else unexpected.
                print_usage(stderr, -1);
        }

    } while (next_option != -1);


    while (1) {
        char buf[MAX_BUF_LEN] = {0};
        bzero(buf, MAX_BUF_LEN);

        get_data(buf, simulate, positive);
        send_data(buf, positive);

        sleep(1);
    }

    return 0;
}


