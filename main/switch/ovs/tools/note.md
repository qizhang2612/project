# 交换机环境依赖

```bash
    sudo apt install redis-server
    sudo apt install libconfig-dev
    sudo apt install autoconf
    sudo apt install libnuma-dev
    sudo apt install python3-pip
    sudo apt install python3-ryu
    sudo apt install libhiredis-dev
    sudo apt install libtool
```

# 控制器

```bash
    pip包依赖
        networkx
        pymysql
    sudo apt install mysql-server
```

# 交换机安装运行open vswitch

1. 编译dpdk-stable-19.11.4
2. 绑定交换机使用的网口到dpdk的igb_uio
3. 执行./config.sh脚本，再执行./build.sh
4. 执行sudo -E ./start.sh以带外模式运行，sudo -E ./in_bind_start.sh以带内模式运行（带内交换机有问题，暂不能运行）
5. 执行./stop-ovs.sh停止open vswitch

交换机在build后，交换机所需的配置文件位于/dev/shm/netstate.cfg，需要修改配置时直接修改此文件

# 交换机的一些配置

## 端口配置

通过dpdk绑定网口到igb_uio，在start.sh脚本里将ovs添加或修改网口，添加网口的命令如下：

```bash
该命令表示添加一个新的网口到br0网桥，网口命名为2，网卡设备号为02:00.0
ovs-vsctl add-port br0 2 -- set Interface 2 type=dpdk     options:dpdk-devargs=0000:02:00.0
```

## controller IP配置

 在start.sh脚本里设置controller地址，也要在/dev/shm/netstate.cfg里同步修改controller地址

# 控制器运行注意事项

## 配置mysql

安装mysql后，修改mysql root用户密码为123456

## 运行方式

按照如下命令运行全部app

```bash
ryu-manager --observe-links netstate/flow_measure.py  simple_switch_13.py topology.py netstate/link_state.py netstate/link_delay.py
```

也可以通过ryu-manager提供的其他方式将所有app加载到一起启动，但要注意的是，在启动过程中发现flow_measure最好在最先启动，否则可能导致后面的被阻塞。**link_delay依赖于link_state和topology**，因此需要先启动依赖app。

## app说明

### link_delay

link delay模块依赖topology模块工作，根据获取的拓扑，每三秒进行一次时延探测，在执行时延探测前会等待30s，让topology模块获取到完整的拓扑。

也可以自行更改等待时间。

### link_state

该模块记录链路的最大容量和链路速率，详情见代码注释

### flow_measure

存储流量测量数据，需注意的是，该模块要早于交换机启动，否则交换机无法建立与控制器接收测量数据的连接。因此应该让控制器整体先启动

在启动交换机。**因此应该让控制器整体先启动在启动交换机。**