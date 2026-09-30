import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import OrderedDict
import queue

from e84_non_RF import E84


class RecordingEventMgr:
    def __init__(self):
        self.events = []

    def on_notify(self, data):
        self.events.append(data)


def make_e84(fw_version="01.03"):
    e84 = E84.__new__(E84)
    e84.event_mgr = RecordingEventMgr()
    e84.fw_version = fw_version
    e84.logger = None
    e84.incoming_queue = queue.Queue(maxsize=100)
    e84.controller = None
    e84.port_no = [1, -1]
    e84.port_id = ["LP1", None]
    e84.port_status = [-1, -1]
    e84.rfid_data = ["", ""]
    e84.mode = [2, -1]
    e84.load = [-1, -1]
    e84.alarm_id = [0, 0]
    e84.alarm_text = ["", ""]
    e84.pspl = -1
    e84.e84_in = -1
    e84.e84_out = -1
    e84.e84_smg = -1
    e84.sensor_elce = -1
    e84.dual = 0
    return e84


def test_send_event_includes_version():
    """send_event must include data['version'] = fw_version (GYRO-300 parity)"""
    e84 = make_e84()
    e84.send_event(code=0x70, subcode=0x0004, msg_text="CS_0 ON")

    assert len(e84.event_mgr.events) == 1
    data = e84.event_mgr.events[0]
    assert data['version'] == "01.03"
    # GYRO-300 field order: version before sw_version
    keys = list(data.keys())
    assert keys.index('version') < keys.index('sw_version')


def test_send_event2_includes_version():
    """send_event2 must include data['version'] = fw_version (GYRO-300 parity)"""
    e84 = make_e84()
    e84.send_event2(code=0x0010, subcode=0x0000, msg_text="test")

    assert len(e84.event_mgr.events) == 1
    data = e84.event_mgr.events[0]
    assert data['version'] == "01.03"
    keys = list(data.keys())
    assert keys.index('version') < keys.index('sw_version')


def test_send_event_version_empty_when_fw_unknown():
    """fw_version may still be '' before the 0x0000 response arrives"""
    e84 = make_e84(fw_version="")
    e84.send_event2(code=0x0000, subcode=0x0000, msg_text="E84 recv 0x0000")

    data = e84.event_mgr.events[0]
    assert data['version'] == ""
