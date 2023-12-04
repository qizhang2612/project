#!/bin/bash

# clean

./stop.sh


sudo ifconfig enp2s0 up
sudo ifconfig enp3s0 up
sudo ifconfig enp1s0 up

sudo ip neigh flush dev enp2s0
sudo ip neigh flush dev enp3s0
sudo ip neigh flush dev enp1s0


sudo ifconfig enp2s0 20.0.0.100/24 up
sudo ifconfig enp3s0 10.0.0.100/24 up



sudo systemctl stop zebra
sudo systemctl stop bgpd
sudo systemctl stop ospfd


sudo systemctl start zebra
sudo systemctl start bgpd
#sudo systemctl restart ospfd


