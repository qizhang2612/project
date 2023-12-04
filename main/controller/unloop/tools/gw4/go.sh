#!/bin/bash

# clean

./stop.sh

# clean end
CONTROLLER=20.0.0.100
LLDP=0x88cc
GPADDRESS=232.0.0.0/16
echo "clean end!!!!"

sudo ovs-vsctl add-br br0
sudo ovs-vsctl add-br br1
sudo ovs-vsctl add-br br2
sudo ovs-vsctl add-br brm

# add veth interfaces

sudo ip link add veth0 type veth peer name veth1
sudo ip link add veth2 type veth peer name veth3
sudo ip link add veth4 type veth peer name veth5
for i in {0..5}
do
    sudo ip link set veth$i up 
done
# end

sudo ifconfig enp3s0 up
sudo ifconfig enp2s0 up
sudo ifconfig enp4s0 up

sudo ip neigh flush dev enp3s0
sudo ip neigh flush dev enp2s0
sudo ip neigh flush dev enp4s0

sudo ovs-vsctl add-port br1 enp3s0
sudo ovs-vsctl add-port br0 enp2s0
sudo ovs-vsctl add-port br2 enp4s0


sudo ovs-vsctl add-port br0 veth3 
sudo ovs-vsctl add-port br1 veth1
sudo ovs-vsctl add-port br2 veth5


sudo ovs-vsctl add-port brm veth0
sudo ovs-vsctl add-port brm veth2
sudo ovs-vsctl add-port brm veth4


sudo ifconfig br0 10.0.6.2/24 up
sudo ifconfig br1 10.0.7.1/24 up
sudo ifconfig br2 10.0.102.1/24 up
sudo ip link set dev brm up


# configure port

sudo ovs-vsctl set Interface enp3s0 ofport_request=1
sudo ovs-vsctl set Interface enp2s0 ofport_request=2

# # add flow entity

sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=veth3, actions=output:enp2s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp2s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=999, eth_type=${LLDP}, in_port=enp2s0, actions=output:veth3"
sudo ovs-ofctl add-flow br0 "table=0 , priority=999, ip, in_port=enp2s0, nw_dst=${GPADDRESS},actions=output:veth3"
sudo ovs-ofctl mod-port br0 veth3 no-flood
sudo ovs-ofctl mod-port br0 enp2s0 no-flood


sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=veth1, actions=output:enp3s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp3s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp3s0, actions=output:veth1"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, ip, in_port=enp3s0, nw_dst=${GPADDRESS}, actions=output:veth1"
sudo ovs-ofctl mod-port br1 veth1 no-flood
sudo ovs-ofctl mod-port br1 enp3s0 no-flood


sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, in_port=veth5, actions=output:enp4s0"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp4s0"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp4s0, actions=output:veth5"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, ip, in_port=enp4s0, nw_dst=${GPADDRESS}, actions=output:veth5"
sudo ovs-ofctl mod-port br2 veth5 no-flood
sudo ovs-ofctl mod-port br2 enp4s0 no-flood


sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd


sudo systemctl restart zebra
sudo systemctl restart bgpd

