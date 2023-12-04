#include "ants-msg.h"
/**
 * 前端接口注意单位：
 * interval: 毫秒
 * duration: 秒
 * period: 秒
 * 但是在程序中为了精度，统一转化成毫秒
 */
void AntsMessageHandler::HandleSetFrequencyMsg(MeasureState *state, void *msg)
{
    if (state == nullptr || msg == nullptr)
        return;
    auto msg_ = reinterpret_cast<SetFrequencyMsg *>(msg);
    state->frequency.duration = msg_->duration * Timer::MSEC_PER_SEC;
    state->frequency.interval = msg_->interval;
    state->frequency.period = msg_->period * Timer::MSEC_PER_SEC;
    LOG(INFO) << "Handle SetFrequency Msg";
    delete msg_;
}

void AntsMessageHandler::HandleSetForceQuitMsg(MeasureState *state, void *msg)
{
    if (state == nullptr || msg == nullptr)
        return;
    auto msg_ = reinterpret_cast<SetForceQuitMsg *>(msg);
    state->force_quit = msg_->force_quit == 1 ? true : false;
    LOG(INFO) << "Handle SetForceQuit Msg";
    delete msg_;
}

void AntsMessageHandler::HandleStartMeasureMsg(MeasureState *state, void *msg)
{
    if (state == nullptr || msg == nullptr)
        return;
    auto msg_ = reinterpret_cast<StartMeasureMsg *>(msg);
    uint64_t now = Timer::tsc_to_ms(Timer::rdtsc());
    state->last_cycle = now - state->frequency.period;
    state->last_time = now;
    state->begin_time = now;
    state->open = true;
    LOG(INFO) << "Handle StartMeasure Msg";
    delete msg_;
}

SetForceQuitMsg *AntsMessageServer::ParseForceQuitMsg(uint8_t *payload)
{
    auto msg = new SetForceQuitMsg();
    msg->force_quit = *payload;
    LOG(INFO) << "parse force quit: " << (int)(msg->force_quit);
    return msg;
}

SetFrequencyMsg *AntsMessageServer::ParseFrequencyMsg(uint8_t *payload)
{
    auto msg = new SetFrequencyMsg();
    msg->interval = be64toh(*reinterpret_cast<uint64_t *>(payload));
    payload += sizeof(uint64_t);
    msg->duration = be64toh(*reinterpret_cast<uint64_t *>(payload));
    payload += sizeof(uint64_t);
    msg->period = be64toh(*reinterpret_cast<uint64_t *>(payload));
    LOG(INFO) << "parse frequency:";
    LOG(INFO) << "interval: " << msg->interval;
    LOG(INFO) << "duration: " << msg->duration;
    LOG(INFO) << "period: " << msg->period;
    return msg;
}

StartMeasureMsg *AntsMessageServer::ParseMeasureMsg(uint8_t *payload)
{
    auto msg = new StartMeasureMsg();
    msg->start = *payload;
    LOG(INFO) << "parse start measure: " << (int)(msg->start);
    return msg;
}
int AntsMessageServer::ParseMsg(int fd, uint16_t type, uint16_t length)
{
    uint8_t buffer[128];
    int read_bytes = length - ANTS_HEADER_LEN;
    LOG(INFO) << "body length: " << read_bytes;
    int n_bytes = read(fd, buffer, read_bytes);
    if (n_bytes != read_bytes)
        return -1;
    void *msg;
    Event e;
    switch (type)
    {
    case SET_FREQUENCY_MSG:
        msg = ParseFrequencyMsg(buffer);
        e = Event(msg, AntsMessageHandler::HandleSetFrequencyMsg);
        event_list->AddEvent(e);
        break;
    case SET_FORCE_QUIT_MSG:
        msg = ParseForceQuitMsg(buffer);
        e = Event(msg, AntsMessageHandler::HandleSetForceQuitMsg);
        event_list->AddEvent(e);
        break;
    case START_MEASURE_MSG:
        msg = ParseMeasureMsg(buffer);
        e = Event(msg, AntsMessageHandler::HandleStartMeasureMsg);
        event_list->AddEvent(e);
        break;
    default:
        break;
    }

    return 0;
}

int SetSocketNonBlock(int sfd)
{
    int flags, s;

    flags = fcntl(sfd, F_GETFL, 0);
    if (flags == -1)
    {
        LOG(ERROR) << "fnctl";
        return -1;
    }

    flags |= O_NONBLOCK;
    s = fcntl(sfd, F_SETFL, flags);
    if (s == -1)
    {
        LOG(ERROR) << "fnctl";
        return -1;
    }

    return 0;
}

void AntsMessageServer::Listen(int &ret)
{
    const int MAX_CONNECTIONS = 20;
    const int MAX_EVENTS = 10;
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == -1)
    {
        LOG(ERROR) << "creating socket failed";
        close(sockfd);
        ret = -1;
        return;
    }
    struct sockaddr_in server_addr;

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(listen_port);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    // 设置端口复用
    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, (const void *)&opt, sizeof(opt));
    if (bind(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        LOG(ERROR) << "binding failed";
        close(sockfd);
        ret = -1;
        return;
    }
    if (listen(sockfd, MAX_CONNECTIONS) < 0)
    {
        LOG(ERROR) << "listening failed";
        close(sockfd);
        ret = -1;
        return;
    }

    int epoll_fd = epoll_create(MAX_EVENTS);
    if (epoll_fd < 0)
    {
        LOG(ERROR) << "epoll_create failed";
        close(sockfd);
        close(epoll_fd);
        ret = -1;
        return;
    }
    //向epoll注册sockfd监听事件
    struct epoll_event ev;                 // epoll事件结构体
    struct epoll_event events[MAX_EVENTS]; //事件监听队列
    ev.events = EPOLLIN | EPOLLET;
    ev.data.fd = sockfd;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, sockfd, &ev) < 0)
    {
        LOG(ERROR) << "start epoll failed";
        close(sockfd);
        close(epoll_fd);
        ret = -1;
        return;
    }

    bool error = false;
    char header[ANTS_HEADER_LEN];
    while (!error && !thread_exit)
    {
        int cnt = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        for (int i = 0; i < cnt; i++)
        {

            if ((events[i].events & EPOLLERR) || (events[i].events & EPOLLHUP) ||
                (!(events[i].events & EPOLLIN)))
            {
                LOG(INFO) << "epoll error";
                close(events[i].data.fd);
                continue;
            }

            // 新客户端连接进来
            if (events[i].data.fd == sockfd)
            {
                // 1. accept
                int connfd = accept(sockfd, NULL, NULL);
                if (connfd < 0)
                {
                    LOG(ERROR) << "accept failed";
                    ret = -1;
                    error = true;
                    break;
                }

                // 2. 设置非阻塞
                SetSocketNonBlock(connfd);

                // 3. 添加epoll事件
                ev.events = EPOLLIN | EPOLLET;
                ev.data.fd = connfd;
                if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, connfd, &ev) < 0)
                {
                    LOG(ERROR) << "epoll_ctl add error!";
                    ret = -1;
                    error = true;
                    break;
                }
                LOG(INFO) << "accept connection";
                continue;
            }

            bool done = false;
            while (true)
            {
                // 获取message header信息
                int n_bytes = read(events[i].data.fd, header, sizeof(header));
                if (n_bytes <= 0)
                {
                    LOG(INFO) << "completed reading all bytes";
                    done = true;
                    break;
                }
                char *p = header;
                uint16_t type = be16toh(*reinterpret_cast<uint16_t *>(p));
                uint16_t length = be16toh(*reinterpret_cast<uint16_t *>(p + sizeof(uint16_t)));
                int re = ParseMsg(events[i].data.fd, type, length);
                if (re < 0)
                {
                    LOG(ERROR) << "parse msg error";
                    ret = -1;
                    error = false;
                    break;
                }
            }

            // 数据接收完毕，关闭连接
            if (done)
            {
                close(events[i].data.fd);
                LOG(INFO) << "disconnect";
            }
        }
    }
    close(sockfd);
    close(epoll_fd);
}
void AntsMessageServer::ServerMain()
{
    int state;
    do
    {
        state = 0;
        Listen(state);
        LOG(INFO) << "try to restart message server";
        std::this_thread::sleep_for(std::chrono::seconds(3));
    } while (state == -1);
}
void AntsMessageServer::StartServer()
{
    LOG(INFO) << "start ants message receive server";
    server_thread = std::thread(&AntsMessageServer::ServerMain, this);
}

void AntsMessageServer::Wait()
{
    server_thread.join();
}

void AntsMessageServer::StopServer()
{
    thread_exit = true;
}