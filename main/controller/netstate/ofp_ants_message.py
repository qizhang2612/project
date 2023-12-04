from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, ofproto_v1_2, ofproto_v1_0


class ANTSMessageSender(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__(*_args, **_kwargs)
        self.vender = 0x00006090
        self.subtype = {
            'NET_STATE_REQUEST_MEASURE': 0x000,
            'NET_STATE_SET_FREQUENCY': 0x001,
            'NET_STATE_SET_FORCE_QUIT': 0x002
        }

    def _send_exp(self, datapath, body, subtype):
        msg = datapath.ofproto_parser.OFPExperimenter(datapath, self.vender, subtype, body)
        datapath.send_msg(msg)

    def request_flow_measure(self, datapath):
        # dummy body
        body = int(16).to_bytes(length=4, byteorder='big', signed=False)
        self._send_exp(datapath=datapath, body=body, subtype=self.subtype['NET_STATE_REQUEST_MEASURE'])

    def set_frequency(self, datapath, frequency):
        period = int(frequency['period']).to_bytes(length=8, byteorder='big', signed=False)
        interval = int(frequency['interval']).to_bytes(length=8, byteorder='big', signed=False)
        duration = int(frequency['duration']).to_bytes(length=8, byteorder='big', signed=False)
        body = period + interval + duration
        self._send_exp(datapath=datapath, body=body, subtype=self.subtype['NET_STATE_SET_FREQUENCY'])

    def set_force_quit(self, datapath, quit_state):
        body = int(quit_state).to_bytes(length=1, byteorder='big', signed=False)
        self._send_exp(datapath=datapath, body=body, subtype=self.subtype['NET_STATE_SET_FORCE_QUIT'])
