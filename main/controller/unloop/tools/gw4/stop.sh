#!/bin/bash

# clean

sudo ovs-vsctl del-br brm
sudo ovs-vsctl del-br br1
sudo ovs-vsctl del-br br0
sudo ovs-vsctl del-br br2

sudo sysctl -p

sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1


sudo ip link del veth0
sudo ip link del veth2
sudo ip link del veth4

sudo ifconfig enp2s0 down
sudo ifconfig enp3s0 down
sudo ifconfig enp4s0 down

#clean end

sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd

