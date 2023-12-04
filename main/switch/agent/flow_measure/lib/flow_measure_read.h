#ifndef _FLOW_MEASURE_READ_H_
#define _FLOW_MEASURE_READ_H_
#include "flow_measure_map.h"
#include "flow_measure_timer.h"
class FlowMeasureReader
{
private:
    static const int SEND_BUF_SIZE;
    static const int MEASURE_DATA_BEGIN;

    std::shared_ptr<PacketStorage> storage_operator[2];
    std::shared_ptr<FlowMeasureControl> timer;
    std::thread reader_thread;
    struct sockaddr_in recv_server;
    bool thread_exit;

    void ReaderMain();

public:
    FlowMeasureReader(std::shared_ptr<PacketStorage> main, std::shared_ptr<PacketStorage> sub,
                      std::shared_ptr<FlowMeasureControl> timer, const std::string &addr, uint16_t port)
    {
        storage_operator[0] = main;
        storage_operator[1] = sub;
        this->timer = timer;
        thread_exit = false;
        recv_server.sin_addr.s_addr = inet_addr(addr.c_str());
        recv_server.sin_family = AF_INET;
        recv_server.sin_port = htons(port);
    }
    void StartReader();
    void Wait();
    void StopReader();
};

#endif // _FLOW_MEASURE_READ_H_