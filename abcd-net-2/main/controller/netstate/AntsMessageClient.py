import socket


class MeasureFrequencyMsg:
    msg_type = 0x01

    def __init__(self, i: int, d: int, p: int) -> None:
        self.interval = i
        self.duration = d
        self.period = p


class ForceQuitMsg:
    msg_type = 0x02

    def __init__(self, quit: int) -> None:
        self.quit = quit


class StartMeasureMsg:
    msg_type = 0x03

    def __init__(self) -> None:
        self.start = 1


class AntsMessageClient:
    '''
    Ants message format:
    -----------------------------------
    |  TCP  | type | length | payload |
    -----------------------------------
    '''

    def __init__(self, server_addr, port=2001) -> None:
        self.port = port
        self.server_addr = server_addr

    def Send(self, content: bytes, info: str):
        sk = socket.socket()
        try:
            sk.connect((self.server_addr, self.port))
            sk.sendall(content)
            print("消息发送成功， 消息类型: {}".format(MeasureFrequencyMsg.__name__))
        except socket.error as e:
            print("发送消息失败，消息类型: {}".format(MeasureFrequencyMsg.__name__))
        sk.close()

    def SendMeasureFrequencyMsg(self, msg: MeasureFrequencyMsg):
        if type(msg) != MeasureFrequencyMsg:
            print("send error, check msg type")
            return
        msg_type = msg.msg_type.to_bytes(
            length=2, byteorder='big', signed=False)
        i = msg.interval.to_bytes(length=8, byteorder='big', signed=False)
        d = msg.duration.to_bytes(length=8, byteorder='big', signed=False)
        p = msg.period.to_bytes(length=8, byteorder='big', signed=False)
        msg_len = len(msg_type) + len(i) + len(d) + len(p) + 2
        length = msg_len.to_bytes(length=2, byteorder='big', signed=False)
        body = msg_type + length + i + d + p

        self.Send(body, MeasureFrequencyMsg.__name__)

    def SendForceQuitMsg(self, msg: ForceQuitMsg):
        if type(msg) != ForceQuitMsg:
            print("send error, check msg type")
            return
        msg_type = msg.msg_type.to_bytes(
            length=2, byteorder='big', signed=False)
        quit = msg.quit.to_bytes(length=1, byteorder='big', signed=False)
        msg_len = len(msg_type) + len(quit) + 2
        length = msg_len.to_bytes(length=2, byteorder='big', signed=False)
        body = msg_type + length + quit

        self.Send(body, ForceQuitMsg.__name__)

    def SendStartMeasureMsg(self, msg: StartMeasureMsg):
        if type(msg) != StartMeasureMsg:
            print("send error, check msg type")
            return
        msg_type = msg.msg_type.to_bytes(
            length=2, byteorder='big', signed=False)
        start = msg.start.to_bytes(length=1, byteorder='big', signed=False)
        msg_len = len(msg_type) + len(start) + 2
        length = msg_len.to_bytes(length=2, byteorder='big', signed=False)
        body = msg_type + length + start

        self.Send(body, StartMeasureMsg.__name__)
