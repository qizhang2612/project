#ifndef _FLOW_MEASURE_MAP_H_
#define _FLOW_MEASURE_MAP_H_
#include "packet_info.h"
#include "crc.h"
#include <tbb/concurrent_hash_map.h>

struct FlowMeasureHashCompare
{
    static size_t hash(const Flow &flow)
    {
        return crc32(reinterpret_cast<const unsigned char *>(&flow), sizeof(flow), 0);
    }

    static bool equal(const Flow &a, const Flow &b)
    {
        return hash(a) == hash(b);
    }
};

class PacketStorage
{
public:
    virtual void Update(const PacketInfo &info) = 0;
    virtual void Reset(const Flow &flow) = 0;
    virtual void DeleteWithKey(const Flow &flow) = 0;
    virtual const tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare> &GetStorageMap() = 0;
};

class FlowMeasureMap : public PacketStorage
{
private:
    tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare> map;

public:
    FlowMeasureMap() = default;
    virtual ~FlowMeasureMap() = default;
    void Update(const PacketInfo &info) override;
    void Reset(const Flow &flow) override;
    void DeleteWithKey(const Flow &flow) override;
    const tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare> &GetStorageMap() override;
};

#endif // _FLOW_MEASURE_MAP_H_