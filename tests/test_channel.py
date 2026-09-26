import asyncio
import types

from e84_client import E84Client
from e84_non_RF import E84
from routers.port import api_port_channel


class DummyLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def test_e84_client_channel_async_returns_true_on_send_success():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()

        send_calls = []

        async def fake_send_CHANNEL_command(channel):
            send_calls.append(channel)
            return True

        client.send_CHANNEL_command = fake_send_CHANNEL_command

        result = await E84Client.channel_async(client, 3)

        assert result is True
        assert send_calls == [3]

    asyncio.run(run_test())


def test_e84_client_channel_async_returns_false_on_send_failure():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()

        async def fake_send_CHANNEL_command(channel):
            return False

        client.send_CHANNEL_command = fake_send_CHANNEL_command

        result = await E84Client.channel_async(client, 3)

        assert result is False

    asyncio.run(run_test())


def test_e84_channel_async_propagates_client_result():
    async def run_test():
        legacy = object.__new__(E84)
        legacy.logger = DummyLogger()

        channel_calls = []

        class DummyClient:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")

            async def channel_async(self, channel):
                channel_calls.append(channel)
                return True

            async def disconnect_async(self):
                self._state.value = "disconnected"

        legacy.e84 = DummyClient()

        result = await E84.channel_async(legacy, 3)

        assert result is True
        assert channel_calls == [3]
        assert legacy.e84._state.value == "disconnected"

    asyncio.run(run_test())


def test_e84_channel_async_returns_false_when_client_fails():
    async def run_test():
        legacy = object.__new__(E84)
        legacy.logger = DummyLogger()

        class DummyClient:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")

            async def channel_async(self, channel):
                return False

            async def disconnect_async(self):
                self._state.value = "disconnected"

        legacy.e84 = DummyClient()

        result = await E84.channel_async(legacy, 3)

        assert result is False

    asyncio.run(run_test())


class DummyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return types.SimpleNamespace(acc_type="USER", userid="tester", name="Tester")


class DummyDB:
    def query(self, *args, **kwargs):
        return DummyQuery()


def build_channel_request(e84_port):
    return types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                glogger=DummyLogger(),
                tsc=types.SimpleNamespace(
                    loadport={1: {'com': 'e84', 'id': 0, 'dual': 0}},
                    e84={0: e84_port},
                ),
            )
        )
    )


def test_api_port_channel_awaits_channel_async_and_reports_failure():
    async def run_test():
        channel_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def channel_async(self, channel):
                channel_calls.append(channel)
                return False

        request = build_channel_request(DummyPort())

        result = await api_port_channel(
            condition=types.SimpleNamespace(port_no=1, enable=True),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 500
        assert "E84 channel operation failed" in result["Message"]
        assert channel_calls == [1]

    asyncio.run(run_test())


def test_api_port_channel_awaits_channel_zero_for_disable():
    async def run_test():
        channel_calls = []

        class DummyE84Client:
            def __init__(self):
                self._state = types.SimpleNamespace(value="connected")
                self.rf_channel_opened_success = False

        class DummyPort:
            def __init__(self):
                self.e84 = DummyE84Client()

            async def channel_async(self, channel):
                channel_calls.append(channel)
                return True

        request = build_channel_request(DummyPort())

        result = await api_port_channel(
            condition=types.SimpleNamespace(port_no=1, enable=False),
            request=request,
            db=DummyDB(),
            login_id="1",
        )

        assert result["Success"] is True
        assert result["State"] == "OK"
        assert result["ErrorCode"] == 0
        assert channel_calls == [0]

    asyncio.run(run_test())
