#include "flow_measure_read.h"

const int FlowMeasureReader::SEND_BUF_SIZE = 2048;
const int FlowMeasureReader::MEASURE_DATA_BEGIN = 4;

void FlowMeasureReader::ReaderMain()
{
    int client_fd;
    int pos;
    int need;
    int flow_count;
    char buffer[2048];
    int sleep_period;
    int sleep_interval;
    std::this_thread::sleep_for(std::chrono::seconds(5));
    need = sizeof(uint32_t) * 2 + sizeof(uint16_t) * 2 + sizeof(uint8_t) + sizeof(uint32_t) * 2;

    int re = -1;
    client_fd = socket(AF_INET, SOCK_STREAM, 0);
    while (re < 0 && !thread_exit)
    {
        re = connect(client_fd, (struct sockaddr *)&recv_server, sizeof(recv_server));
        LOG(INFO) << "try to connect to flow measure server";
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    LOG(INFO) << "successfully connect to flow measure server";
    close(client_fd);

    sleep_interval = timer->Interval() / 5;
    sleep_period = timer->Period() / 5;
    while (!thread_exit)
    {
        if (timer->Readable() == false)
        {
            if (timer->Paused())
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_period));
            else
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_interval));
            continue;
        }
        /*connect with flow measure server*/
        client_fd = socket(AF_INET, SOCK_STREAM, 0);
        re = connect(client_fd, (struct sockaddr *)&recv_server, sizeof(recv_server));
        if (re < 0)
        {
            LOG(ERROR) << "failed to connect with flow measure server";
            return;
        }

        /*clear buffer and reset data position*/
        memset(buffer, 0, SEND_BUF_SIZE);
        pos = MEASURE_DATA_BEGIN;
        flow_count = 0;
        /**
         * 1. switch to read table
         * 2. iterate the hash map
         * 3. read flow data from redis sequentially
         */
        int read_idx = timer->GetCurrentReadIndex();
        auto &map = storage_operator[read_idx]->GetStorageMap();
        std::vector<Flow> del;
        for (auto iter = map.begin(); iter != map.end(); iter++)
        {
            if (iter->second.bytes == 0 || iter->second.count == 0)
            {
                del.push_back(iter->first);
                continue;
            }
            if (SEND_BUF_SIZE < pos + need)
            {
                memcpy(buffer, &flow_count, sizeof(uint32_t));
                if (send(client_fd, buffer, pos, 0) < 0)
                    LOG(ERROR) << "send measure data to controller failed!";
                memset(buffer, 0, SEND_BUF_SIZE);
                pos = MEASURE_DATA_BEGIN;
                flow_count = 0;
            }

            // 1. copy five tuple
            memcpy(buffer + pos, &(iter->first.src_ip), sizeof(uint32_t));
            pos += sizeof(uint32_t);
            memcpy(buffer + pos, &(iter->first.dst_ip), sizeof(uint32_t));
            pos += sizeof(uint32_t);
            memcpy(buffer + pos, &(iter->first.src_port), sizeof(uint16_t));
            pos += sizeof(uint16_t);
            memcpy(buffer + pos, &(iter->first.dst_port), sizeof(uint16_t));
            pos += sizeof(uint16_t);
            memcpy(buffer + pos, &(iter->first.protocol), sizeof(uint8_t));
            pos += sizeof(uint8_t);

            // 2. copy pkt data
            memcpy(buffer + pos, &(iter->second.bytes), sizeof(uint32_t));
            pos += sizeof(uint32_t);
            memcpy(buffer + pos, &(iter->second.count), sizeof(uint32_t));
            pos += sizeof(uint32_t);

            // 3. reset flow measure data
            flow_count++;
            storage_operator[read_idx]->Reset(iter->first);
        }
        // 清理过期flow
        for (auto &flow : del)
            storage_operator[read_idx]->DeleteWithKey(flow);
        if (pos > MEASURE_DATA_BEGIN)
        {
            memcpy(buffer, &flow_count, sizeof(uint32_t));
            if (send(client_fd, buffer, pos, 0) < 0)
                LOG(ERROR) << "send measure data to controller failed!";
        }
        timer->SetUnReadable();
        close(client_fd);
    }
}
void FlowMeasureReader::StartReader()
{
    LOG(INFO) << ("start reader thread");
    reader_thread = std::thread(&FlowMeasureReader::ReaderMain, this);
}
void FlowMeasureReader::Wait()
{
    reader_thread.join();
}
void FlowMeasureReader::StopReader()
{
    thread_exit = true;
}