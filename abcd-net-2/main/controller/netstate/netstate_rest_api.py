from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
from urllib.parse import parse_qs
from netstate_config import *
import AntsMessageClient as ants


class FlowMeasureController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.flow_measure_app = data[app_flow_measure_name]

    @route('flow_measure', url_start_flow_measure, methods=['POST'])
    def start_flow_measure(self, req, **kwargs):
        if req.body:
            body = req.body.decode('utf-8')
        else:
            return Response(status=500)
        data = parse_qs(body)
        if data.get('switch_id'):
            switch_id = int(data.get('switch_id')[0])
            addr = self.flow_measure_app.dpid_to_addr[switch_id][0]
            client = ants.AntsMessageClient(addr)
            msg = ants.StartMeasureMsg()
            client.SendStartMeasureMsg(msg)
        else:
            print("bad request body, without switch_id")
        return Response(status=200)

    @route('flow_measure', url_open_flow_measure, methods=['POST'])
    def open_flow_measure(self, req, **kwargs):
        if req.body:
            body = req.body.decode('utf-8')
        else:
            return Response(status=500)
        data = parse_qs(body)
        if data.get('switch_id'):
            switch_id = int(data.get('switch_id')[0])
            addr = self.flow_measure_app.dpid_to_addr[switch_id][0]
            client = ants.AntsMessageClient(addr)
            msg = ants.ForceQuitMsg(0)
            client.SendForceQuitMsg(msg)
        else:
            print("bad request body, without switch_id")
        return Response(status=200)

    @route('flow_measure', url_close_flow_measure, methods=['POST'])
    def close_flow_measure(self, req, **kwargs):
        if req.body:
            body = req.body.decode('utf-8')
        else:
            return Response(status=500)
        data = parse_qs(body)
        if data.get('switch_id'):
            switch_id = int(data.get('switch_id')[0])
            addr = self.flow_measure_app.dpid_to_addr[switch_id][0]
            client = ants.AntsMessageClient(addr)
            msg = ants.ForceQuitMsg(1)
            client.SendForceQuitMsg(msg)
        else:
            print("bad request body, without switch_id")
        return Response(status=200)

    @route('flow_measure', url_set_frequency, methods=['POST'])
    def set_frequency(self, req, **kwargs):
        if req.body:
            body = req.body.decode('utf-8')
        else:
            return Response(status=500)

        data = parse_qs(body)
        try:
            switch_id = int(data.get('switch_id')[0])
            period = int(data.get('period')[0])
            duration = int(data.get('duration')[0])
            interval = int(data.get('interval')[0])
            switch_id = int(data.get('switch_id')[0])
            addr = self.flow_measure_app.dpid_to_addr[switch_id][0]
            client = ants.AntsMessageClient(addr)
            msg = ants.MeasureFrequencyMsg(i=interval, d=duration, p=period)
            client.SendMeasureFrequencyMsg(msg)
        except Exception as e:
            print(e)
        return Response(status=200)
