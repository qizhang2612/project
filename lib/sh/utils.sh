#!/bin/bash

#######################################
# Print error message
#######################################
err () {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

#######################################
# Get the NIC device name to reach a given host
# Arguments:
#   Host name
# Outputs:
#   NIC name
#######################################
get_out_dev () {
    local USAGE="Usage: ${FUNCNAME[0]} HOST_NAME"
    if (($# < 1)); then
        echo "$USAGE" >&2
        exit
    fi
    local host="$1"
    local ip="$(python3 -c "import socket; print(socket.gethostbyname(\"$host\"))")"
    ip route get $ip | grep -o "dev.*" | cut -d ' ' -f 2
}

#######################################
# Get the physical NIC device name to reach a given host
# Arguments:
#   Host name
# Outputs:
#   NIC name
#######################################
get_phy_out_dev () {
    local USAGE="Usage: ${FUNCNAME[0]} HOST_NAME"
    if (($# < 1)); then
        echo "$USAGE" >&2
        exit
    fi
    local host="$1"
    local ip="$(python3 -c "import socket; print(socket.gethostbyname(\"$host\"))")"
    local dev="$(ip route get $ip | grep -o "dev.*" | cut -d ' ' -f 2)"
    if [[ "$dev" == "lo" ]]; then
        echo $dev
        return
    fi
    while [ ! -e /sys/class/net/$dev/device ]; do
        local drv="$(ethtool -i $dev | grep driver | cut -d' ' -f2)"
        if [[ "$drv" == 'bridge' ]]; then
            ping -c 1 -i 0.2 $ip > /dev/null || err "ping $ip exits with error"
            local dmac=$(ip neigh show $ip | grep -o "lladdr.*" | cut -d ' ' -f 2)
            if [[ -z "$dmac" ]]; then
                err "Cannot resolve the mac address of $ip"
                exit 1
            fi
            dev=$(bridge fdb get $dmac br $dev | grep -o "dev.*" | cut -d ' ' -f 2)
        else
            err "Unknown device type: $drv"
            exit 1
        fi
    done
    echo $dev
}

#######################################
# Get Operating System name
# Outputs:
#   OS name (macos/ubuntu)
#######################################
get_os_name () {
    case $(uname -s) in
        Darwin) echo 'macos';;
        Linux) cat '/etc/os-release' |  grep -i '^id=' | awk -F= '{print $2}' ;;
    esac
}

#######################################
# Get CPU architecture
# Outputs:
#   CPU architecture (amd64/arm64)
#######################################
get_cpu_arch () {
    case $(uname -m) in
        i386)   echo '386' ;;
        i686)   echo '386' ;;
        x86_64) echo 'amd64' ;;
        aarch64) echo 'arm64' ;;
    esac
}

#######################################
# Quietly install package with homebrew
# Arguments:
#   Package names
#######################################
brew_install_quiet () {
    for formula in $@; do
        brew list $formula &> /dev/null || brew install $formula
    done
}

#######################################
# Install packages in different Operating systems
# Arguments:
#   Package names
#######################################
install_pkg () {
    if (($# == 0)); then
        return
    fi
    local os_name=$(get_os_name)
    if [ -n "$(echo $os_name | grep -i 'centos')" ]; then
        sudo yum install -y $@
    elif [ -n "$(echo $os_name | grep -i 'ubuntu')" ]; then
        sudo apt install -y $@
    elif [ -n "$(echo $os_name | grep -i 'arch')" ]; then
        sudo pacman -Su --noconfirm --needed $@
    elif [ -n "$(echo $os_name | grep -i 'macos')" ]; then
        brew_install_quiet $@
    else
        echo "Unknown OS: $os_name"
        exit 1
    fi
}


#######################################
# Backup directory by moving this directory to the archive directory
# Arguments:
#  Directory path to backup
#  Archive directory name
#######################################
backup_dir () {
    local USAGE="Usage: ${FUNCNAME[0]} DIRECTORY [ARCHIVE_DIRECTORY]"
    if (($# < 1)); then
        echo $USAGE
        exit
    fi
    local dirname="$1"
    local archivedir="$(dirname $dirname)/archives"
    if (($# >= 2)); then
        archivedir="$2"
    fi
    if [ -e "$dirname" ] && [ -n "$(ls $dirname)" ]; then
        local postfix=$(date +'%Y%m%d%H%M%S')
        mkdir -p $archivedir
        mv $dirname $archivedir/$(basename $dirname)-$postfix
    fi
}

#######################################
# Bind the rx irq of a network device of a cpu
# Args:
#   Network interface name
#   CPU ID to bind the rx irq to
#######################################
bind_rxirq_to_cpu () {
    local USAGE="Usage: ${FUNCNAME[0]} DEVNAME CPU_ID"
    if (($# < 2)); then
        echo $USAGE
        exit
    fi
    local devname="$1"
    local cpuid="$2"
    # `irqbalance` tries to automatically balance IRQs to CPUs
    # and it may overwrite the CPU affinity settings.
    pgrep irqbalance && sudo systemctl stop irqbalance.service
    for irqnum in $(grep $devname /proc/interrupts | awk -F':' '{print $1}'); do
        sudo bash -c "echo $cpuid > /proc/irq/$irqnum/smp_affinity_list"
    done
}

#######################################
# Remove a qdisc from all devices
# Args:
#   qdisc name
#######################################
remove_qdisc () {
    local USAGE="${FUNCNAME[0]} QDISC"
    if (($# < 1)); then
        echo $USAGE
        exit
    fi
    local qdisc="$1"
    for dev in $(ip link show | grep '^[0-9]\+' | cut -d':' -f2); do
        if [[ -n "$(tc qdisc show dev $dev | cut -d' ' -f2 | grep "^${qdisc}$")" ]]; then
            sudo tc qdisc del dev $dev root
        fi
    done
}

#######################################
# Remove a packet scheduling kernel module
# Args:
#   kernel module name
#   qdisc name of this kernel module
#######################################
remove_sch_mod () {
    local USAGE="${FUNCNAME[0]} MODULE_NAME QDISC_NAME"
    if (($# < 2)); then
        echo $USAGE
        exit
    fi
    local modname="$1"
    local qdisc="$2"
    local n_used=$(lsmod | grep "^${modname}\\s" | awk '{print $3}')
    if [[ -n "$n_used" ]]; then
        if (($n_used > 0)); then
            remove_qdisc $qdisc
        fi
        sudo rmmod $modname
    fi
}
