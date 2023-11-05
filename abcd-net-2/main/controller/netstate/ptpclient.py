import socket
import time
import subprocess
import os
import multiprocessing
import copy



ip_port = ('20.0.0.20', 9999)
password = "1"
portlist = ["enp1s0","enp2s0","enp3s0","enp4s0","enp5s0","enp6s0"]

#关闭NTP
def do_close_ntp():
    command1 = 'timedatectl set-ntp false'
    command2 = 'systemctl restart systemd-timesyncd.service'
    os.system('echo %s | sudo -S %s' % (password,command1))
    os.system('echo %s | sudo -S %s' % (password,command2))

#关闭NTP并执行PTP时钟同步(主)
def do_ptp_master(s):
    command = 'timeout 2m ptp4l -2 -A -i'+s+' --step_threshold=1 -m -H'
    os.system('echo %s | sudo -S %s' % (password,command))

#执行PTP时钟同步(副)
def do_ptp_slave(s):
    command = 'timeout 2m ptp4l -2 -A -i'+s+' --step_threshold=1 -m -H -s'
    os.system('echo %s | sudo -S %s' % (password,command))
    
#同步到系统时钟
def do_sync_to_sc(s):
    command = 'timeout 2m phc2sys -m -s CLOCK_REALTIME -c '+s+' -w'
    os.system('echo %s | sudo -S %s' % (password,command))

#交换机上所有端口统一时钟
def switch_all_clocksync(s):
    portlist1 = []
    for port in portlist:
        if port != s:
            portlist1.append(port)
        else:
            continue 
    # creating processes 
    p1 = multiprocessing.Process(target=do_ptp_master,args=(s,))
    p2 = multiprocessing.Process(target=do_sync_to_sc,args=(s,))
    p3 = multiprocessing.Process(target=do_ptp_slave,args=(portlist1[0],))
    p4 = multiprocessing.Process(target=do_sync_to_sc,args=(portlist1[0],))
    p5 = multiprocessing.Process(target=do_ptp_slave,args=(portlist1[1],))
    p6 = multiprocessing.Process(target=do_sync_to_sc,args=(portlist1[1],))
    p7 = multiprocessing.Process(target=do_ptp_slave,args=(portlist1[2],))
    p8 = multiprocessing.Process(target=do_sync_to_sc,args=(portlist1[2],))
    p9 = multiprocessing.Process(target=do_ptp_slave,args=(portlist1[3],))
    p10 = multiprocessing.Process(target=do_sync_to_sc,args=(portlist1[3],))
    p11 = multiprocessing.Process(target=do_ptp_slave,args=(portlist1[4],))
    p12 = multiprocessing.Process(target=do_sync_to_sc,args=(portlist1[4],))
    # starting process
    p1.start()
    p2.start()
    p3.start()
    p4.start()
    p5.start()
    p6.start()
    p7.start()
    p8.start()
    p9.start()
    p10.start()
    p11.start()
    p12.start()
    # wait until process is finished 
    p1.join()
    p2.join()
    p3.join()
    p4.join()
    p5.join()
    p6.join()
    p7.join()
    p8.join()
    p9.join()
    p10.join()
    p11.join()
    p12.join()
    # both processes finished 
    print("Done!")

#主时钟执行
def master_process_exec(s):
    # creating processes 
    p1 = multiprocessing.Process(target=do_close_ntp) 
    p2 = multiprocessing.Process(target=do_ptp_master,args=(s,)) 
    p3 = multiprocessing.Process(target=do_sync_to_sc,args=(s,)) 
    # starting process
    p1.start() 
    p2.start()
    p3.start() 
    # wait until process is finished 
    p1.join() 
    p2.join()
    p3.join() 
    # both processes finished 
    print("Done!")

#从时钟执行
def slave_process_exec(s):
    # creating processes 
    p1 = multiprocessing.Process(target=do_close_ntp) 
    p2 = multiprocessing.Process(target=do_ptp_slave,args=(s,)) 
    p3 = multiprocessing.Process(target=do_sync_to_sc,args=(s,)) 
    # starting process
    p1.start() 
    p2.start()
    p3.start() 
    # wait until process is finished 
    p1.join() 
    p2.join()
    p3.join() 
    # both processes finished 
    print("Done!")

def main():
    # 创建套接字
    sk = socket.socket()  
    # 绑定服务地址          
    sk.bind(ip_port)
    # 监听连接请求                
    sk.listen(5)                    
    print('启动socket服务，等待客户端连接...')
    # 等待连接，此处自动阻塞
    conn, address = sk.accept()   
    while True:   
        # 接收信息  
        client_data = conn.recv(1024).decode()     
        s1 = client_data[0]
        s2 = client_data[1:]
        if(s1 == "M" or s1 == "S" or s1 == "T"):
            conn.sendall('finish'.encode())
            break
    conn.close()    
    if(s1 == "M"):
        master_process_exec(s2)
        switch_all_clocksync(s2)
    elif(s1 == "S"):
        slave_process_exec(s2)
        switch_all_clocksync(s2)
    else:
        print("error")

main()
