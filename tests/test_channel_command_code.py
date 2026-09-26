import asyncio
import types

import pytest

from e84_client import E84Client, E84Command
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


def test_channel_and_db25_share_command_code_no_duplicate_enum():
    assert E84Command.DB25_PORT == 0x8001
    assert not hasattr(E84Command, 'CHANNEL')


def test_send_channel_command_uses_db25_port_code():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()

        send_calls = []

        async def fake_send_e84_command(command, param, timeout=5.0):
            send_calls.append((command, param))
            return object()

        client._send_e84_command = fake_send_e84_command

        result = await E84Client.send_CHANNEL_command(client, 3)

        assert result is True
        assert send_calls == [(E84Command.DB25_PORT, 3)]

    asyncio.run(run_test())


def test_send_channel_command_returns_false_without_response():
    async def run_test():
        client = object.__new__(E84Client)
        client.logger = DummyLogger()

        async def fake_send_e84_command(command, param, timeout=5.0):
            return None

        client._send_e84_command = fake_send_e84_command

        result = await E84Client.send_CHANNEL_command(client, 3)

        assert result is False

    asyncio.run(run_test())
