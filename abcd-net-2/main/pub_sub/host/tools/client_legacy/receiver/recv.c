#include <stdio.h>
#include "../lib/json/cJSON.h"
#include "unistd.h"
#include "sys/socket.h"
#include "netinet/in.h"
#include "arpa/inet.h"
#include "string.h"
#include "stdlib.h"

#define MAX_BUF_LEN 512
#define PORT 9000



// Build a socket and
// wait for topic's message
int main() {
    // Build a socket
    struct sockaddr_in from, addr_recv;
    int len = sizeof(addr_recv);
    int fd_recv = socket(AF_INET, SOCK_DGRAM, 0);
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_port = htons(PORT);

    char *json_path = "ip.json";
    FILE *fp = fopen(json_path, "r");
    char config_content[MAX_BUF_LEN];
    fread(config_content, sizeof(int), MAX_BUF_LEN, fp);
    cJSON *config = (cJSON *) cJSON_Parse(config_content);
    cJSON *cjson_ip = cJSON_GetObjectItem(config, "ip");
    addr_recv.sin_addr.s_addr = inet_addr(cjson_ip->valuestring);
    
    bind(fd_recv, (struct sockaddr *) &addr_recv, len);
    printf("receiving data on address %s...\n", cjson_ip->valuestring);
    fflush(stdout);

    char buf[MAX_BUF_LEN] = {0};

    // Continuously listen a port to receive topic's message
    while (1) {
        bzero(buf, MAX_BUF_LEN);
        recvfrom(fd_recv, buf, MAX_BUF_LEN, 0, (struct sockaddr *) &addr_recv, &len);
        printf("recv: %s\n", buf);
        fflush(stdout);
    }

    close(fd_recv);
    return 0;
}
