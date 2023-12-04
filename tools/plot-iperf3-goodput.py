import argparse
import matplotlib.pyplot as plt

import lib.py.net.iperf3 as iperf3
import lib.py.plot.plot as myplot

def main():
    parser = argparse.ArgumentParser(description='Plot iperf3 logs')
    parser.add_argument('logs', help='log file name')
    args = parser.parse_args()
    iperfjson = iperf3.Iperf3Json(args.logs)
    # lp = myplot.LinePlot()
    fig, ax = plt.subplots()
    if len(iperfjson.throughput_per_flow) > 1:
        for fid in iperfjson.throughput_per_flow:
            ax.plot(
                iperfjson.throughput_per_flow[fid]['time'],
                iperfjson.throughput_per_flow[fid]['bits_per_second']/1e6,
                label=('flow' + str(fid)),
            )
    ax.plot(
        iperfjson.throughput['time'],
        iperfjson.throughput['bits_per_second']/1e6,
        label='Total',
    )
    ax.legend()
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Goodput (Mbps)')
    plt.legend(loc='best')
    plt.show()


if __name__ == '__main__':
    main()
