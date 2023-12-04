sudo ip link set dev enp1s0f0 down
sudo ip link set del 10.0.101/24 dev enp1s0f0

sudo ip addr add 10.0.101.2/24 dev enp1s0f0

sudo ip link set dev enp1s0f0 up

sudo route add -net 10.0.0.0/24 gw 10.0.101.1
sudo route add -net 20.0.0.0/24 gw 10.0.101.1
sudo route add -net 232.0.0.0/24 dev enp1s0f0

