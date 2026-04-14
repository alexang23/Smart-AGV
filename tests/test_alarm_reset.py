import asyncio
import types

from e84_client import E84Client, E84Command, E84Protocol
from smart_e84 import SmartE84


class DummyLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def build_read_frame(command, data=0x0000, status=0x00):
    frame = (
        E84Protocol.HEADER_READ
        + bytes([(command >> 8) & 0xFF, command & 0xFF, (data >> 8) & 0xFF, data & 0xFF, status])
    )
    checksum = E84Protocol.calculate_checksum(frame)
    return frame + bytes([checksum])


def test_e84_client_alarm_reset_returns_false_on_send_failure():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()

        async def fake_send_e84_command(command, param):
            return None

        client._send_e84_command = fake_send_e84_command

        result = await E84Client.alarm_reset(client)

        assert result is False

    asyncio.run(run_test())


def test_e84_response_parser_returns_full_frame_for_command_dispatch():
    client = object.__new__(E84Client)
    client.logger = DummyLogger()
    client._on_message_event = None
    client._on_sensor_event = None
    client._on_state_event = None
    client._on_alarm_event = None
    client._last_message = None

    response_frame = build_read_frame(E84Command.ALARM_RESET)

    command_id, response_data = E84Client._e84_response_parser(client, response_frame)

    assert command_id == "E84_8002"
    assert response_data == response_frame


def test_send_e84_command_uses_matched_response_when_last_message_changes():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()
        client._last_message = None

        alarm_reset_response = build_read_frame(E84Command.ALARM_RESET)
        follow_up_event = build_read_frame(0x0070, 0x0001)

        async def fake_send_command_async(command_id, data, timeout):
            client._last_message = E84Protocol.parse_message(follow_up_event)
            return alarm_reset_response

        client.send_command_async = fake_send_command_async

        result = await E84Client._send_e84_command(client, E84Command.ALARM_RESET, 0x0000)

        assert result is not None
        assert result.command == E84Command.ALARM_RESET

    asyncio.run(run_test())


def test_smart_e84_alarm_reset_connects_before_send():
    async def run_test():
        smart = object.__new__(SmartE84)
        smart.logger = DummyLogger()

        class DummyE84:
            def __init__(self):
                self._state = types.SimpleNamespace(value="disconnected")
                self.connect_calls = 0
                self.alarm_reset_calls = 0

            async def connect_async(self):
                self.connect_calls += 1
                self._state.value = "connected"

            async def alarm_reset(self):
                self.alarm_reset_calls += 1
                return True

        smart.e84 = DummyE84()

        result = await SmartE84.alarm_reset_async(smart)

        assert result is True
        assert smart.e84.connect_calls == 1
        assert smart.e84.alarm_reset_calls == 1

    asyncio.run(run_test())
