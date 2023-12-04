#ifndef _CAPTURE_H_
#define _CAPTURE_H_
#include <pcap.h>
#include <arpa/inet.h>
#include <cstring>
#include <string>
#include <memory>
#include <future>
#include <netinet/in.h>
#include <netinet/ether.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <netinet/if_ether.h>
#include "flow_measure_map.h"
#include "flow_measure_timer.h"

/**
 * Capture packet from a NIC
 */
class PacketCapture
{
private:
    std::string device;
    std::shared_ptr<PacketStorage> storage_operator[2];
    std::shared_ptr<FlowMeasureControl> timer;
    std::thread capture_thread;
    pcap_t *handle;

    static void PacketHandler(u_char *capture, const struct pcap_pkthdr *header, const u_char *packet);
    void CaptureMain();

public:
    PacketCapture(const std::string &dev, std::shared_ptr<PacketStorage> main,
                  std::shared_ptr<PacketStorage> sub, std::shared_ptr<FlowMeasureControl> timer) : device(dev)
    {
        storage_operator[0] = main;
        storage_operator[1] = sub;
        this->timer = timer;
    }
    void StartPacketProcess();
    void Wait();
    void StopCapture();
};

#endif