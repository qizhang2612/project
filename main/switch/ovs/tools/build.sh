#! /bin/sh
set -eux

OVS_HOME="$HOME/abcd-net/main/switch"
OVS_BIN_DIR="/usr/local/bin"
OVS_CONF_DIR="/usr/local/etc/openvswitch"
OVS_HEADER_DIR="/usr/local/include/openvswitch"
OVS_LIB_DIR="/usr/local/lib"
OVS_SBIN_DIR="/usr/local/sbin"
OVS_SCRIPT_DIR="/usr/local/share/openvswitch"

cd "$OVS_HOME" || exit

# Unset proxy
# unset http_proxy
# unset https_proxy


echo "Delete previous build target files..."
sudo rm -rf "$OVS_BIN_DIR/ovs*"
sudo rm -rf "$OVS_CONF_DIR"
sudo rm -rf "$OVS_HEADER_DIR"
sudo rm -rf "$OVS_LIB_DIR/libo*"
sudo rm -rf "$OVS_SBIN_DIR/ovs*"
sudo rm -rf "$OVS_SCRIPT_DIR"

#./configure --with-dpdk="$DPDK_BUILD"
make -j8 || exit
sudo make install
sudo /sbin/modprobe openvswitch
sudo /sbin/lsmod | grep openvswitch

cp "lib/netstate/netstate.cfg" /dev/shm/