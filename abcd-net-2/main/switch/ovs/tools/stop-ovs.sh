#!/bin/bash
set -ux

sudo ovs-vsctl del-br br0
sudo ovs-ctl stop
ps aux | grep ovs-vswitchd | grep -v grep | awk '{print $2}' | xargs sudo kill -9 || :
