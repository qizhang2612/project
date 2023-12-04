#!/bin/bash

# clean

./stop.sh

# clean end

CONTROLLER="20.0.0.100"
LLDP=0x88cc
GPADDRESS=232.0.0.0/16

echo "clean end!!!!"

sudo ovs-vsctl add-br br0
sudo ovs-vsctl add-br br1
sudo ovs-vsctl add-br brm

# add veth interfaces

sudo ip link add veth0 type veth peer name veth1
sudo ip link add veth2 type veth peer name veth3
for i in {0..3}
do
	    sudo ip link set veth$i up 
done
# end

sudo ifconfig enp1s0 up
sudo ifconfig enp2s0 up
sudo ip neigh flush dev enp1s0
sudo ip neigh flush dev enp2s0


sudo ovs-vsctl add-port br0 enp2s0
sudo ovs-vsctl add-port br1 enp1s0


sudo ovs-vsctl add-port br0 veth3 
sudo ovs-vsctl add-port br1 veth1


sudo ovs-vsctl add-port brm veth0
sudo ovs-vsctl add-port brm veth2


sudo ifconfig br0 10.0.4.1/24 up
sudo ifconfig br1 10.0.7.2/24 up
sudo ip link set dev brm up



# configure port

sudo ovs-vsctl set Interface enp1s0 ofport_request=4
sudo ovs-vsctl set Interface enp2s0 ofport_request=5

# add flow entity

sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=veth3, actions=output:enp2s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp2s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp2s0, actions=output:veth3"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, ip, in_port=enp2s0, nw_dst=${GPADDRESS}, actions=output:veth3"
sudo ovs-ofctl mod-port br0 veth3 no-flood
sudo ovs-ofctl mod-port br0 enp2s0 no-flood


sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=veth1, actions=output:enp1s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp1s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp1s0, actions=output:veth1"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, ip, in_port=enp1s0, nw_dst=${GPADDRESS}, actions=output:veth1"
sudo ovs-ofctl mod-port br1 veth1 no-flood
sudo ovs-ofctl mod-port br1 enp1s0 no-flood




sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd

sudo systemctl restart zebra
sudo systemctl restart bgpd


