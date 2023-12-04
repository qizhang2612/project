#!/bin/bash

# clean

./stop.sh

# clean end

sudo ovs-vsctl add-br brm
sudo ovs-vsctl add-br br0
sudo ovs-vsctl add-br br1
sudo ovs-vsctl add-br br2
sudo ovs-vsctl add-br br3
sudo ovs-vsctl add-br br4

echo "clean end!!!!"

CONTROLLER=20.0.0.100
LLDP=0x88cc
GPADDRESS=232.0.0.0/16

# add veth interfaces

sudo ip link add veth0 type veth peer name veth1
sudo ip link add veth2 type veth peer name veth3
sudo ip link add veth4 type veth peer name veth5
sudo ip link add veth6 type veth peer name veth7
sudo ip link add veth8 type veth peer name veth9
for i in {0..9}
do
    sudo ip link set veth$i up 
done
# end

sudo ifconfig enp1s0 up
sudo ifconfig enp2s0 up
sudo ifconfig enp3s0 up
sudo ifconfig enp4s0 up
sudo ifconfig enp6s0 up


sudo ip neigh flush dev enp1s0
sudo ip neigh flush dev enp2s0
sudo ip neigh flush dev enp3s0
sudo ip neigh flush dev enp4s0
sudo ip neigh flush dev enp6s0

sudo ovs-vsctl add-port br0 enp1s0
sudo ovs-vsctl add-port br1 enp6s0
sudo ovs-vsctl add-port br2 enp3s0
sudo ovs-vsctl add-port br3 enp2s0
sudo ovs-vsctl add-port br4 enp4s0


sudo ovs-vsctl add-port br0 veth3
sudo ovs-vsctl add-port br1 veth1
sudo ovs-vsctl add-port br2 veth5
sudo ovs-vsctl add-port br3 veth7
sudo ovs-vsctl add-port br4 veth9


sudo ovs-vsctl add-port brm veth2
sudo ovs-vsctl add-port brm veth6
sudo ovs-vsctl add-port brm veth4
sudo ovs-vsctl add-port brm veth8
sudo ovs-vsctl add-port brm veth0


sudo ip link set dev br0 up
sudo ip link set dev br1 up
sudo ip link set dev br2 up
sudo ip link set dev br3 up
sudo ip link set dev br4 up
sudo ip link set dev brm up


# configure port

sudo ovs-vsctl set Interface enp1s0 ofport_request=1
sudo ovs-vsctl set Interface enp2s0 ofport_request=2
sudo ovs-vsctl set Interface enp3s0 ofport_request=3
sudo ovs-vsctl set Interface enp4s0 ofport_request=4
sudo ovs-vsctl set Interface enp6s0 ofport_request=5

# add flow entity

sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=veth3, actions=output:enp1s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp1s0"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp1s0, actions=output:veth3"
sudo ovs-ofctl add-flow br0 "table=0 , priority=1000, ip, in_port=enp1s0, nw_dst=${GPADDRESS}, actions=output:veth3"
sudo ovs-ofctl mod-port br0 veth3 no-flood
sudo ovs-ofctl mod-port br0 enp1s0 no-flood


sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=veth1, actions=output:enp6s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp6s0"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp6s0, actions=output:veth1"
sudo ovs-ofctl add-flow br1 "table=0 , priority=1000, ip, in_port=enp6s0, nw_dst=${GPADDRESS}, actions=output:veth1"
sudo ovs-ofctl mod-port br1 veth1 no-flood
sudo ovs-ofctl mod-port br1 enp6s0 no-flood
 

sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, in_port=veth5, actions=output:enp3s0"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp3s0"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, eth_type=${LLDP}, in_port=enp3s0, actions=output:veth5"
sudo ovs-ofctl add-flow br2 "table=0 , priority=1000, ip, in_port=enp3s0, nw_dst=${GPADDRESS}, actions=output:veth5"
sudo ovs-ofctl mod-port br2 veth5 no-flood
sudo ovs-ofctl mod-port br2 enp3s0 no-flood
 

sudo ovs-ofctl add-flow br3 "table=0, priority=1000, in_port=veth7, actions=output:enp2s0"
sudo ovs-ofctl add-flow br3 "table=0 , priority=1000, in_port=LOCAL, actions=output:enp2s0"
sudo ovs-ofctl add-flow br3 "table=0, priority=1000, eth_type=${LLDP}, in_port=enp2s0, actions=output:veth7"
sudo ovs-ofctl add-flow br3 "table=0, priority=1000, ip, in_port=enp2s0, nw_dst=${GPADDRESS}, actions=output:veth7"
sudo ovs-ofctl mod-port br3 veth7 no-flood
sudo ovs-ofctl mod-port br3 enp2s0 no-flood

sudo ovs-ofctl add-flow br4 "table=0, priority=1000, in_port=veth9, actions=output:enp4s0"
sudo ovs-ofctl add-flow br4 "table=0, priority=1000, in_port=LOCAL, actions=output:enp4s0"
sudo ovs-ofctl add-flow br4 "table=0, priority=1000, eth_type=${LLDP}, in_port=enp4s0, actions=output:veth9"
sudo ovs-ofctl add-flow br4 "table=0, priority=1000, ip, in_port=enp4s0, nw_dst=${GPADDRESS}, actions=output:veth9"
sudo ovs-ofctl mod-port br4 veth9 no-flood
sudo ovs-ofctl mod-port br4 enp4s0 no-flood


sudo ip addr add 10.0.4.2/24 dev br0
sudo ip addr add 10.0.6.1/24  dev br1
sudo ip addr add 20.0.0.99/24 dev br2
sudo ip addr add 10.0.0.99/24 dev br3
sudo ip addr add 10.0.101.1/24 dev br4

sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd


sudo systemctl start zebra
sudo systemctl start bgpd


