import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import e84_non_RF
from e84_non_RF import E84

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class RecordingEventMgr:
    """Record every payload pushed through on_notify"""

    def __init__(self):
        self.events = []


def make_e84_for_init():
    e84 = E84.__new__(E84)
    e84.event_mgr = RecordingEventMgr()
    e84.fw_version = ""
    e84.logger = MagicMock()
    e84.devPath = "COM_TEST"
    e84.e84 = MagicMock()
    return e84


@pytest.mark.parametrize("raw,expected", [
    ((0x01, 0x03), "01.03"),
    ((0x25, 0x00), "25.00"),
])
async def test_init_e84_stores_firmware_version(raw, expected):
    """init_e84 must store read_firmware_version result into self.fw_version (GYRO-300 parity)"""
    e84 = make_e84_for_init()

    fake_client = MagicMock()
    fake_client.connect_async = AsyncMock()
    fake_client.initialize_device = AsyncMock(return_value=True)
    fake_client.read_firmware_version = AsyncMock(return_value=raw)
    fake_client.disconnect_async = AsyncMock()
    state = MagicMock()
    state.value = "connected"
    fake_client._state = state
    e84.e84 = None  # init_e84 creates its own client

    # skip constructor-created E84Client: inject factory via settings-independent path
    import e84_non_RF
    orig_client = e84_non_RF.E84Client
    e84_non_RF.E84Client = MagicMock(return_value=fake_client)
    try:
        await e84.init_e84()
    finally:
        e84_non_RF.E84Client = orig_client

    assert e84.fw_version == expected, f"expected {expected}, got {e84.fw_version!r}"
    e84.handler_task.cancel()
    try:
        await e84.handler_task
    except asyncio.CancelledError:
        pass


async def test_init_e84_keeps_empty_fw_version_on_query_failure():
    """If read_firmware_version fails/returns None, fw_version stays ''"""
    e84 = make_e84_for_init()

    fake_client = MagicMock()
    fake_client.connect_async = AsyncMock()
    fake_client.initialize_device = AsyncMock(return_value=True)
    fake_client.read_firmware_version = AsyncMock(return_value=None)
    fake_client.disconnect_async = AsyncMock()
    state = MagicMock()
    state.value = "connected"
    fake_client._state = state
    e84.e84 = None

    import e84_non_RF
    orig_client = e84_non_RF.E84Client
    e84_non_RF.E84Client = MagicMock(return_value=fake_client)
    try:
        await e84.init_e84()
    finally:
        e84_non_RF.E84Client = orig_client

    assert e84.fw_version == ""
    e84.handler_task.cancel()
    try:
        await e84.handler_task
    except asyncio.CancelledError:
        pass
