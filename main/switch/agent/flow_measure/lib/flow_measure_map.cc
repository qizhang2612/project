#include "flow_measure_map.h"

/**
 * @brief
 * update flow measure data for a packet
 * @param info
 */
void FlowMeasureMap::Update(const PacketInfo &info)
{
    tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare>::accessor result;
    if (map.find(result, info.flow))
    {
        result->second.bytes += info.statistics.bytes;
        result->second.count++;
    }
    else
        map.insert({info.flow, info.statistics});
}

/**
 * @brief
 * set a item's size and cnt to zero in map
 * @param flow_hash
 */
void FlowMeasureMap::Reset(const Flow &flow)
{
    tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare>::accessor result;
    if (map.find(result, flow))
    {
        result->second.bytes = 0;
        result->second.count = 0;
    }
}

void FlowMeasureMap::DeleteWithKey(const Flow &flow)
{
    tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare>::accessor result;
    if (map.find(result, flow))
    {
        map.erase(result);
    }
}

const tbb::concurrent_hash_map<Flow, Statistics, FlowMeasureHashCompare> &FlowMeasureMap::GetStorageMap()
{
    return map;
}