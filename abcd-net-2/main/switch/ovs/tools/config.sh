#! /bin/sh
set -eux

OVS_HOME="$HOME/abcd-net/main/switch"
DPDK_BUILD="$HOME/dpdk-stable-19.11.4/x86_64-native-linux-gcc"
export CLFAGS="-mavx"
cd "$OVS_HOME" || exit

./boot.sh
./configure --with-dpdk="$DPDK_BUILD"