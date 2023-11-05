#ifndef _ANTS_MSG_H_
#define _ANTS_MSG_H_
#include <cstdint>
#include <memory>
#include <arpa/inet.h>
#include <glog/logging.h>
#include <sys/epoll.h>
#include <netinet/in.h>
#include <errno.h>
#include <fcntl.h>
#include "event-list.h"
#include "../lib/flow_measure_timer.h"

enum AntsMessageType
{
    SET_FREQUENCY_MSG = 0x01,
    SET_FORCE_QUIT_MSG,
    START_MEASURE_MSG
};

struct AntsHeader
{
    uint16_t type;
    uint16_t length;
};
static const int ANTS_HEADER_LEN = sizeof(uint16_t) + sizeof(uint16_t);

struct SetFrequencyMsg
{
    AntsHeader hdr;
    uint64_t interval; // millisecond
    uint64_t duration; // second
    uint64_t period;   // second
};
static const int SET_FREQUENCY_BODY_LEN = sizeof(uint64_t) * 3;

struct SetForceQuitMsg
{
    AntsHeader hdr;
    uint8_t force_quit;
};
static const int SET_FORCE_QUIT_BODY_LEN = sizeof(uint8_t);

struct StartMeasureMsg
{
    AntsHeader hdr;
    uint8_t start;
};
static const int START_MEASURE_BODY_LEN = sizeof(uint8_t);

class AntsMessageHandler
{
public:
    static void HandleSetFrequencyMsg(MeasureState *state, void *msg);
    static void HandleSetForceQuitMsg(MeasureState *state, void *msg);
    static void HandleStartMeasureMsg(MeasureState *state, void *msg);
};

class AntsMessageServer
{
private:
    uint16_t listen_port;
    std::shared_ptr<EventList> event_list;
    std::thread server_thread;
    bool thread_exit;

    SetForceQuitMsg *ParseForceQuitMsg(uint8_t *payload);
    SetFrequencyMsg *ParseFrequencyMsg(uint8_t *payload);
    StartMeasureMsg *ParseMeasureMsg(uint8_t *payload);
    int ParseMsg(int fd, uint16_t type, uint16_t length);
    void ServerMain();

public:
    AntsMessageServer(std::shared_ptr<EventList> events_list, uint16_t port = 2001)
    {
        listen_port = port;
        this->event_list = events_list;
        thread_exit = false;
    }
    void Listen(int &ret);
    void StartServer();
    void StopServer();
    void Wait();
};

#endif // _ANTS_MSG_H_