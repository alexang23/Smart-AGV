import json
from collections import OrderedDict

import pytest

from e84_non_RF import E84


class RecordingEventMgr:
    """Record every payload pushed through on_notify"""

    def __init__(self):
        self.events = []

    def on_notify(self, data):
        self.events.append(data)


def make_e84():
    e84 = E84.__new__(E84)
    e84.event_mgr = RecordingEventMgr()
    e84.logger = None  # not used unless errors occur
    e84.incoming_queue = __import__("queue").Queue(maxsize=100)
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


def build_frame(command: int, data_word: int) -> bytes:
    """Minimal valid E84 frame for E84Protocol.parse_message (READ header, event frames are READ type)"""
    from e84_client import E84Protocol

    body = E84Protocol.HEADER_READ + bytes(
        [(command >> 8) & 0xFF, command & 0xFF, (data_word >> 8) & 0xFF, data_word & 0xFF, 0x00]
    )
    return body + bytes([E84Protocol.calculate_checksum(body)])


def _active_e84_events(mgr):
    return [json.loads(e if isinstance(e, str) else json.dumps(e)) for e in mgr.events]


def test_e84_message_does_not_publish_0x70_event_frames():
    """0x70 signal frame should be queued for the run loop only, not published from callback"""
    e84 = make_e84()
    frame = build_frame(0x70, 0x0004)

    e84.e84_message(frame)

    assert len(e84.incoming_queue.queue) == 1, "frame must still be queued for run loop"
    active_events = [
        e for e in e84.event_mgr.events if isinstance(e, OrderedDict) and e.get("topic") == "Active-E84"
    ]
    assert not active_events, (
        f"e84_message must not publish Active-E84 events, got {len(active_events)}: "
        f"{[dict(e) for e in active_events]}"
    )


@pytest.mark.parametrize("command,data_word", [(0x70, 0x0004), (0x71, 0x0001), (0x80, 0x0001)])
def test_e84_message_does_not_publish_any_event_series(command, data_word):
    e84 = make_e84()
    frame = build_frame(command, data_word)

    e84.e84_message(frame)

    active_events = [
        e for e in e84.event_mgr.events if isinstance(e, OrderedDict) and e.get("topic") == "Active-E84"
    ]
    assert not active_events, f"command 0x{command:04X} published {len(active_events)} events from callback"
    assert e84.incoming_queue.qsize() == 1, "frame must still be queued for run loop"


def test_e84_message_queues_frame_before_notifying():
    """The queue must receive the frame regardless of publish-path changes"""
    e84 = make_e84()
    frame = build_frame(0x70, 0x0004)

    e84.e84_message(frame)

    queued = list(e84.incoming_queue.queue)
    assert frame in queued
