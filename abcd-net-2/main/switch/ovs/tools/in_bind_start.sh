#!/bin/bash
set -eux

# Run in sudo mode
CPU_MASK=0xfff
CONTROLLER_SOCKET="20.0.0.1:6633"

OVS_HOME="$HOME/abcd-net/main/switch"
OVS_CONF_DIR="/usr/local/etc/openvswitch"
OVS_RUN_DIR="/usr/local/var/run/openvswitch"
OVS_LOG_DIR="/usr/local/var/log/openvswitch"
OVS_SCRIPT_DIR="/usr/local/share/openvswitch"
cp "$OVS_HOME/lib/netstate/netstate.cfg" /dev/shm/

echo "Step 0. Close all existing ovs processes"
export PATH=$PATH:$OVS_SCRIPT_DIR/scripts
ovs-ctl stop
echo "Step 1. Check OpenVSwitch config..."
# Check if OVS_CONF_DIR exists
if [ ! -d "$OVS_CONF_DIR" ]; then
  echo "Create directory $OVS_CONF_DIR"
  mkdir -p "$OVS_CONF_DIR"
fi
# Check if OpenVSwitchDaemon config file exists
if [ ! -f "$OVS_CONF_DIR/conf.db" ]; then
  echo "Create file $OVS_CONF_DIR/conf.db"
  ovsdb-tool create $OVS_CONF_DIR/conf.db "$OVS_HOME"/vswitchd/vswitch.ovsschema
fi
# Check if OVS log directory exists
if [ ! -d "$OVS_LOG_DIR" ]; then
  echo "Create directory $OVS_LOG_DIR"
  mkdir -p "$OVS_LOG_DIR"
fi

rm /usr/local/var/log/openvswitch/ovs-vswitchd.log ||

echo "============================================================================="

echo "Step 2. Run OpenVSwitch database..."
# Check if OpenVSwitch Runtime directory exists
if [ ! -d "$OVS_RUN_DIR" ]; then
  echo "Create directory $OVS_RUN_DIR"
  mkdir -p "$OVS_RUN_DIR"
fi
ovsdb-server --remote=punix:$OVS_RUN_DIR/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --private-key=db:Open_vSwitch,SSL,private_key \
    --certificate=db:Open_vSwitch,SSL,certificate \
    --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
    --pidfile --detach --log-file
echo "============================================================================="

echo "Step 3. Setup OpenVSwitch and run"
export DB_SOCK=$OVS_RUN_DIR/db.sock
ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
ovs-vsctl set Open_vSwitch . other_config:pmd-cpu-mask=$CPU_MASK
ovs-ctl --no-ovsdb-server --db-sock="$DB_SOCK" start

ovs-vsctl add-br br0 -- set bridge br0 datapath_type=netdev
ovs-vsctl add-port br0 1 -- set Interface 1 type=dpdk     options:dpdk-devargs=0000:01:00.0
ovs-vsctl add-port br0 3 -- set Interface 3 type=dpdk     options:dpdk-devargs=0000:03:00.0
ovs-vsctl add-port br0 2 -- set Interface 2 type=dpdk     options:dpdk-devargs=0000:02:00.0
#ovs-vsctl set interface 3 options:n_rxq=3 other_config:pmd-rxq-affinity="0:4,1:5,2:6"
#ovs-vsctl set interface 4 options:n_rxq=3 other_config:pmd-rxq-affinity="0:0,1:1,2:2"
ifconfig br0 20.0.0.30/24
ovs-vsctl set-controller br0 tcp:$CONTROLLER_SOCKET
ovs-vsctl set bridge br0 other-config:datapath-id=0000000000000001
echo "============================================================================="

echo "Step 4. Check OpenVSwitch status..."
ovs-vsctl show
ovs-vsctl get Open_vSwitch . dpdk_initialized
ovs-vswitchd --version
ovs-vsctl get Open_vSwitch . dpdk_version

# delete all flow tables
#ovs-ofctl del-flows br0
#ovs-vsctl set-fail-mode br0 secure

#ovs-ofctl add-flow br0 in_port=2,actions=OUTPUT:1 -O OpenFlow13
#ovs-ofctl add-flow br0 in_port=1,actions=OUTPUT:2 -O OpenFlow13
