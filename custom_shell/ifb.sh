#/bin/bash
set -eux

modprobe ifb
ip link set dev $2 up
tc qdisc replace dev $1 ingress
tc filter replace dev $1 parent ffff: protocol ip u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev $2
tc qdisc replace dev $2 root netem delay 10ms
