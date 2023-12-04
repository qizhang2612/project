"""The startup program.
"""
from ryu.cmd import manager

# add '--ofp-listen-host=10.0.100.1' for in-band mode


if __name__ == '__main__':
    file_path = './main/controller/manager/controller.py'
    debug = True
    observe_links = True
    # debug
    debug = False
    if debug:
        file_path = '/home/sleepwalker/wwb-code/wwb-abcd-net/main/controller/manager/controller.py'

    run_args = ['--app-lists', file_path,
                '--enable-debugger', '--verbose',
                '--ofp-listen-host=20.0.0.100']
    if observe_links:
        run_args.append('--observe-links')

    manager.main(run_args)

