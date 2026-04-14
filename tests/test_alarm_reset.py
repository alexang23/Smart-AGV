import asyncio
import types

from e84_client import E84Client, E84Command, E84Protocol, E84StateEvent
from e84 import E84
from serial_gyro import AsyncSerialPort
from smart_e84 import SmartE84
from routers.port import api_port_arm_back, api_port_channel, api_port_handoff


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


def test_e84_client_arm_back_complete_requires_completion_state():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()
        client._last_state_event_code = E84StateEvent.HANDOFF_COMPLETE
        client._last_state_event_description = E84StateEvent.get_description(E84StateEvent.HANDOFF_COMPLETE)

        send_calls = []

        async def fake_send_e84_command(command, param):
            send_calls.append((command, param))
            return object()

        client._send_e84_command = fake_send_e84_command

        result = await E84Client.arm_back_complete(client, ready_timeout=0.0)

        assert result is False
        assert send_calls == []

    asyncio.run(run_test())


def test_e84_client_arm_back_complete_sends_after_load_complete():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()
        client._last_state_event_code = E84StateEvent.LOAD_COMPLETE
        client._last_state_event_description = E84StateEvent.get_description(E84StateEvent.LOAD_COMPLETE)

        send_calls = []

        async def fake_send_e84_command(command, param):
            send_calls.append((command, param))
            return object()

        client._send_e84_command = fake_send_e84_command

        result = await E84Client.arm_back_complete(client, ready_timeout=0.0)

        assert result is True
        assert send_calls == [(E84Command.ARM_BACK, 0x0001)]

    asyncio.run(run_test())


def test_e84_client_state_event_updates_arm_back_gate():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()
        client._on_state_event = None
        client._event_queue = None
        client._event_queue_size = None
        client._event_queue_loop = None
        client._last_state_event_code = None
        client._last_state_event_description = ""

        message = E84Protocol.parse_message(build_read_frame(0x0071, E84StateEvent.UNLOAD_COMPLETE))

        await E84Client._handle_state_event(client, message)

        assert client._last_state_event_code == E84StateEvent.UNLOAD_COMPLETE
        assert client._last_state_event_description == E84StateEvent.get_description(E84StateEvent.UNLOAD_COMPLETE)
        assert client._can_send_arm_back() is True

    asyncio.run(run_test())


def test_api_port_arm_back_returns_fail_when_called_too_early():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        arm_back_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")

            def _can_send_arm_back(self):
                return False

            async def arm_back_complete(self, is_unload=False, ready_timeout=30.0):
                arm_back_calls.append((is_unload, ready_timeout))
                return True

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def _ensure_e84_connected(self, operation_name: str, attempts: int = 3):
                return True

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_arm_back(
            condition=types.SimpleNamespace(port_no=1),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 500
        assert "Load Complete or Unload Complete" in result["Message"]
        assert arm_back_calls == []

    asyncio.run(run_test())


def test_api_port_handoff_returns_fail_when_rf_channel_not_opened():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        handoff_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            def run_cmd(self, command):
                handoff_calls.append(command)

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_handoff(
            condition=types.SimpleNamespace(port_no=1, cs=0, task=0),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 500
        assert "Open RF channel successfully" in result["Message"]
        assert handoff_calls == []

    asyncio.run(run_test())


def test_api_port_handoff_runs_after_rf_channel_opened():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        handoff_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = True

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            def run_cmd(self, command):
                handoff_calls.append(command)

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_handoff(
            condition=types.SimpleNamespace(port_no=1, cs=1, task=0),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is True
        assert result["State"] == "OK"
        assert result["ErrorCode"] == 0
        assert handoff_calls == ["handoff 1 0"]

    asyncio.run(run_test())


def test_api_port_channel_returns_fail_when_rf_channel_open_fails():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        channel_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def open_RF_channel(self):
                channel_calls.append("open")
                return False

            async def alarm_reset_async(self):
                channel_calls.append("reset")
                return True

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_channel(
            condition=types.SimpleNamespace(port_no=1, enable=True),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 500
        assert "RF channel open failed" in result["Message"]
        assert channel_calls == ["open"]

    asyncio.run(run_test())


def test_api_port_channel_returns_success_when_rf_channel_open_succeeds():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        channel_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def open_RF_channel(self):
                channel_calls.append("open")
                self.e84.rf_channel_opened_success = True
                return True

            async def alarm_reset_async(self):
                channel_calls.append("reset")
                return True

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_channel(
            condition=types.SimpleNamespace(port_no=1, enable=True),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is True
        assert result["State"] == "OK"
        assert result["ErrorCode"] == 0
        assert result["Message"] == ""
        assert channel_calls == ["open"]

    asyncio.run(run_test())


def test_api_port_channel_returns_fail_when_alarm_reset_fails():
    async def run_test():
        login_user = types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")

        class DummyQuery:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return login_user

        class DummyDB:
            def query(self, *args, **kwargs):
                return DummyQuery()

        channel_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = True

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def open_RF_channel(self):
                channel_calls.append("open")
                return True

            async def alarm_reset_async(self):
                channel_calls.append("reset")
                return False

        request = types.SimpleNamespace(
            app=types.SimpleNamespace(
                state=types.SimpleNamespace(
                    glogger=DummyLogger(),
                    tsc=types.SimpleNamespace(
                        loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                        e84={0: DummyPort()},
                    ),
                )
            )
        )

        result = await api_port_channel(
            condition=types.SimpleNamespace(port_no=1, enable=False),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 500
        assert "RF channel reset failed" in result["Message"]
        assert channel_calls == ["reset"]
        assert request.app.state.tsc.e84[0].e84.rf_channel_opened_success is False

    asyncio.run(run_test())


def test_e84_client_connect_async_returns_parent_result():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()
        client._event_queue = None
        client._event_queue_size = 1
        client._event_queue_loop = None

        connect_calls = []
        original_connect_async = AsyncSerialPort.connect_async

        async def fake_connect_async(self, *args, **kwargs):
            connect_calls.append((args, kwargs))
            return True

        AsyncSerialPort.connect_async = fake_connect_async
        try:
            result = await E84Client.connect_async(client)
        finally:
            AsyncSerialPort.connect_async = original_connect_async

        assert result is True
        assert len(connect_calls) == 1
        assert client._event_queue is not None
        assert client._event_queue_loop is asyncio.get_running_loop()

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


def test_legacy_e84_alarm_reset_async_returns_bool_and_clears_rf_channel_flag():
    async def run_test():
        legacy = object.__new__(E84)

        class DummyE84Device:
            def __init__(self):
                self.rf_channel_opened_success = True
                self.alarm_reset_calls = 0

            async def alarm_reset(self):
                self.alarm_reset_calls += 1
                return True

        legacy.e84 = DummyE84Device()

        result = await E84.alarm_reset_async(legacy)

        assert result is True
        assert legacy.e84.rf_channel_opened_success is False
        assert legacy.e84.alarm_reset_calls == 1

    asyncio.run(run_test())


def test_smart_e84_open_rf_channel_marks_ready_on_success():
    async def run_test():
        smart = object.__new__(SmartE84)
        smart.logger = DummyLogger()

        class DummyE84:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False
                self.initialize_calls = 0
                self.disconnect_calls = 0

            async def initialize_COMport_RFsensor(self):
                self.initialize_calls += 1
                return True

            async def disconnect_async(self):
                self.disconnect_calls += 1
                self._state.value = "disconnected"

        smart.e84 = DummyE84()

        result = await SmartE84.open_RF_channel(smart)

        assert result is True
        assert smart.e84.rf_channel_opened_success is True
        assert smart.e84.initialize_calls == 1
        assert smart.e84.disconnect_calls == 1

    asyncio.run(run_test())
