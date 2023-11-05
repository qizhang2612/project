#!/bin/bash
set -eux

#tc qdisc replace dev $1 root handle 800: netem delay 10ms
tc qdisc add dev $1 root  handle 1: htb  default 11
tc class add dev $1 parent 1:  classid 1:1 htb  rate 20Mbit ceil 20Mbit
tc class add dev $1 parent 1:1 classid 1:10 htb rate 128kbit ceil 20Mbit  prio 3 
tc class add dev $1 parent 1:1 classid 1:11 htb rate 128kbit ceil 20Mbit  prio 2 
tc class add dev $1 parent 1:1 classid 1:12 htb rate 128kbit ceil 20Mbit  prio 1 

# config codel
tc qdisc add dev $1 parent 1:10 codel target 15ms interval 100ms  ecn
tc qdisc add dev $1 parent 1:11 codel target 15ms interval 100ms  ecn
tc qdisc add dev $1 parent 1:12 codel target 15ms interval 100ms  ecn


# tc class add dev $1 parent 1:1 classid 1:12 htb rate 20000kbps ceil 20Mbit  prio 1 
tc filter add dev $1 protocol ip parent 1: prio 1 u32 match ip dport 81 0xffff flowid 1:11
tc filter add dev $1 protocol ip parent 1: prio 1 u32 match ip dport 82 0xffff flowid 1:12

# configure controller priority
#tc filter add dev $1 protocol ip parent 1: prio 1 u32 match ip dport 6633 0xffff flowid 1:12
#tc filter add dev $1 protocol ip parent 1: prio 1 u32 match ip sport 6633 0xffff flowid 1:12
