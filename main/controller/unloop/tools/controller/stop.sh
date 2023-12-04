#!/bin/bash

# clean
sudo sysctl -p


sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1



sudo ifconfig enp2s0 down
sudo ifconfig enp3s0 down
sudo ifconfig enp1s0 down

sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd

# clean end

echo "clean end!!!!"


