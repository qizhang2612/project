#include <stdio.h>
#include <string.h>
#include "/tmp/CLion/client/lib/json/cJSON.h"
#include "unistd.h"
#include "sys/socket.h"
#include "netinet/in.h"
#include "arpa/inet.h"
#include "string.h"
#include "stdlib.h"

#define IP "232.0.0.1"
#define RECV_IP "10.0.0.1"
#define MAX_BUF_LEN 512
#define CONTROLLER_PORT 8888
#define DATA_PORT 8889


// Load the configuring file
//
// Args:
//  config_content: A point pointing a buffer
//                 used to save the json string,
//                 and it should not be empty
//
// We use the file's path to get json file and transfer it
// into the json string and save it into the config_content pointing
// buffer
void load_conf(char *config_content) {
    char *json_path = "config.json";
    FILE *fp = fopen(json_path, "r");
    fread(config_content, sizeof(int), MAX_BUF_LEN, fp);

    cJSON *config = (cJSON *) cJSON_Parse(config_content);

    if (config == NULL) {
        printf("config file parse failed.\n");
        exit(1);
    }

    cJSON *cjson_name = cJSON_GetObjectItem(config, "name");
    cJSON *cjson_type = cJSON_GetObjectItem(config, "type");
    cJSON *cjson_location = cJSON_GetObjectItem(config, "location");
    cJSON *cjson_description = cJSON_GetObjectItem(config, "description");

    if (!cjson_name || !cjson_type || !cjson_location || !cjson_description) {
        printf("miss requested properties in config file.\n");
        exit(1);
    }

    char *config_str = cJSON_Print(config);
    printf("local info:\n%s\n", config_str);
}


// Parsing the command string
//
// Args:
//  buf: A point pointing the command string representing user's input
//  type: A point pointing a buffer used to save the
//       extra parameters of user's input
int parse_cmd_type(char *buf, char *type) {
    int i = 0, j = 0;
    int buf_len = strlen(buf);

    while (i < buf_len && buf[i] == ' ') i++;

    while (i < buf_len) {
        if (buf[i] != ' ' && buf[i] != '\n') type[j++] = buf[i++];
        else break;
    }

    type[j] = '\0';

    if (strcmp(type, "pub") != 0 && strcmp(type, "reg") != 0 &&
        strcmp(type, "pull") != 0 && strcmp(type, "search") != 0
        && strcmp(type, "sub") != 0) {
        printf("wrong cmd type, cmd should in [reg, pub, pull, search, sub].\n");
        return 0;
    }

    return 1;
}


// Just contract two strings and put it into
// a buffer
void generate_config_request(char *buf, char *type, char *config_content) {
    strcpy(buf, type);
    strcat(buf, " ");
    strcat(buf, config_content);
}


// Just contract some strings and put it
// into a buffer
void save_msg(char *type, char *address, char *location, char *topic_name, int fd_data) {
    char buf[MAX_BUF_LEN] = {0};

    strcat(buf, type);
    strcat(buf, " ");
    strcat(buf, address);
    strcat(buf, " ");
    strcat(buf, location);
    strcat(buf, " ");
    strcat(buf, topic_name);
    send(fd_data, buf, strlen(buf), 0);

    return;
}


// Build a socket to connect the local database
// return the built socket, which is just a integer
int create_data_connection() {
    // data socket.
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


// Parse the result from controller
//
// Args:
//  type: A string representing the type of the command
//  buf: A string representing the reply of the controller
void parse_result(char *type, char *buf) {
    // parse result from controller.
    cJSON *cjson_result = (cJSON *) cJSON_Parse(buf);
    char *result_str = cJSON_Print(cjson_result);
    printf("controller: \n%s\n", result_str);

    if (cjson_result == NULL) {
        printf("reply from controller parse failed, check data format!!!\n");
        return;
    }

    cJSON *cjson_status = (cJSON *) cJSON_GetObjectItem(cjson_result, "status");
    cJSON *cjson_msg = (cJSON *) cJSON_GetObjectItem(cjson_result, "msg");

    if (strcmp(cjson_status->valuestring, "failed") == 0) {
        return;
    }

    // To solve pub command, we save the topic's
    // information to the local database, which
    // contains group address of the topic, the location of the topic
    // and the topic's name
    if (strcmp(type, "pub") == 0) {
        cJSON *cjson_group_addr = (cJSON *) cJSON_GetObjectItem(cjson_result, "group_addr");
        cJSON *cjson_location = (cJSON *) cJSON_GetObjectItem(cjson_result, "location");
        cJSON *cjson_topic_name = (cJSON *) cJSON_GetObjectItem(cjson_result, "topic_name");

        int fd_data = create_data_connection();
        save_msg(type, cjson_group_addr->valuestring,
                 cjson_location->valuestring, cjson_topic_name->valuestring, fd_data);
        close(fd_data);
        return;
    }

    // To solve sub command, we save the subscribing
    // information to the local database, which
    // contains ipv4_address of the topic, the location of the topic
    // and the topic's name
    if (strcmp(type, "sub") == 0) {
        cJSON *cjson_pub_ipv4 = (cJSON *) cJSON_GetObjectItem(cjson_result, "pub_ipv4");
        cJSON *cjson_location = (cJSON *) cJSON_GetObjectItem(cjson_result, "location");
        cJSON *cjson_topic_name = (cJSON *) cJSON_GetObjectItem(cjson_result, "topic_name");

        int fd_data = create_data_connection();
        save_msg(type, cjson_pub_ipv4->valuestring,
                 cjson_location->valuestring, cjson_topic_name->valuestring, fd_data);
        close(fd_data);
        return;
    }

}

int main() {
    char *json_path = "ip.json";
    FILE *fp = fopen(json_path, "r");

    char ip[MAX_BUF_LEN];
    fread(ip, sizeof(int), MAX_BUF_LEN, fp);
    cJSON *config = (cJSON *) cJSON_Parse(ip);
    cJSON *cjson_ip = cJSON_GetObjectItem(config, "ip");

    // To build a socket connected to the controller,
    // and the code is too lengthy, so I strongly suggest you
    // use and read the python version of these C code
    int fd = 0, len = 0, fd_recv = 0;
    struct sockaddr_in List_buf, List_buf_recv;
    len = sizeof(List_buf);

    fd = socket(AF_INET, SOCK_DGRAM, 0);
    List_buf.sin_family = AF_INET;
    List_buf.sin_port = htons(CONTROLLER_PORT);
    List_buf.sin_addr.s_addr = inet_addr(IP);
    bind(fd, (struct sockaddr *) &List_buf, len);

    fd_recv = socket(AF_INET, SOCK_DGRAM, 0);
    List_buf_recv.sin_family = AF_INET;
    List_buf_recv.sin_port = htons(CONTROLLER_PORT);
    List_buf_recv.sin_addr.s_addr = inet_addr(cjson_ip->valuestring);
    bind(fd_recv, (struct sockaddr *) &List_buf_recv, len);

    char buf[MAX_BUF_LEN] = {0};
    char config_content[MAX_BUF_LEN] = {0};

    // Get user's input and parse it.
    // If it is legal input, just transfer it
    // into a querying string and send it to
    // the controller.
    while (1) {
        bzero(buf, MAX_BUF_LEN);
        printf("pub_sub >> ");
        fflush(stdout);
        fgets(buf, MAX_BUF_LEN, stdin);

        // judge cmd type, decorate msg send to controller.
        // cmd type: [reg, pub, pull, search, sub].
        char type[MAX_BUF_LEN];
        int success = parse_cmd_type(buf, type);
        if (!success) continue;

        if (strcmp(type, "pub") == 0 || strcmp(type, "reg") == 0) {
            load_conf(config_content);
            generate_config_request(buf, type, config_content);
        }

        sendto(fd, buf, strlen(buf), 0, (struct sockaddr *) &List_buf, len);
        bzero(buf, 512);
        recvfrom(fd_recv, buf, 512, 0, (struct sockaddr *) &List_buf_recv, &len);

        parse_result(type, buf);
    }

    close(fd);
    close(fd_recv);
    return 0;
}
