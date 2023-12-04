#include <iostream>
#include "message/ants-msg.h"
#include "lib/flow_measure_timer.h"
#include "lib/capture.h"
#include "lib/flow_measure_read.h"
int main()
{
    // 测试代码
    // TODO 添加配置文件，从配置文件解析参数
    std::shared_ptr<EventList> msg_mail(new EventList());
    std::shared_ptr<AntsMessageServer> server(new AntsMessageServer(msg_mail, 2001));
    std::shared_ptr<FlowMeasureTimer> timer(new FlowMeasureTimer(3, 200, 5, msg_mail));
    std::shared_ptr<FlowMeasureControl> control(timer);
    std::shared_ptr<PacketStorage> storage_main(new FlowMeasureMap());
    std::shared_ptr<PacketStorage> storage_sub(new FlowMeasureMap());
    std::shared_ptr<PacketCapture> capture1(new PacketCapture("enp1s0", storage_main, storage_sub, control));
    std::shared_ptr<PacketCapture> capture2(new PacketCapture("enp2s0", storage_main, storage_sub, control));
    std::shared_ptr<FlowMeasureReader> reader(new FlowMeasureReader(storage_main, storage_sub, timer, "20.0.0.1", 7777));
    server->StartServer();
    timer->StartTimer();
    capture1->StartPacketProcess();
    capture2->StartPacketProcess();
    reader->StartReader();

    server->Wait();
    timer->Wait();
    capture1->Wait();
    capture2->Wait();
    reader->Wait();
    return 0;
}