import asyncio
import types

import serial_gyro
from serial_gyro import AsyncSerialPort, ConnectionState, SerialPortIdentity


class DummyWriter:
    def __init__(self):
        self.closed = False

    def is_closing(self):
        return self.closed

    def close(self):
        self.closed = True

    async def wait_closed(self):
        return None


class DummyReader:
    async def read(self, size):
        return b"\x01"


class EOFReader:
    async def read(self, size):
        return b""


def test_async_serial_connect_async_switches_to_reenumerated_port():
    async def run_test():
        original_start_event_loop = AsyncSerialPort._start_event_loop
        original_open = serial_gyro.serial_asyncio.open_serial_connection
        original_comports = serial_gyro.list_ports.comports

        open_calls = []
        port_entry = types.SimpleNamespace(
            device="COM16",
            serial_number="ABC123",
            location="1-1",
            vid=0x1234,
            pid=0x5678,
            manufacturer="Gyro",
            product="E84",
            interface=None,
        )

        async def noop_loop():
            return None

        async def fake_open_serial_connection(*, url, baudrate, bytesize, parity, stopbits):
            open_calls.append(url)
            if url == "COM14":
                raise serial_gyro.serial.SerialException("could not open port 'COM14'")
            return DummyReader(), DummyWriter()

        AsyncSerialPort._start_event_loop = lambda self: None
        serial_gyro.serial_asyncio.open_serial_connection = fake_open_serial_connection
        serial_gyro.list_ports.comports = lambda: [port_entry]

        try:
            serial_port = AsyncSerialPort("COM14", auto_reconnect=False)
            serial_port._response_reader_loop = noop_loop
            serial_port._timeout_checker_loop = noop_loop
            serial_port._port_identity = SerialPortIdentity(
                serial_number="ABC123",
                location="1-1",
                vid=0x1234,
                pid=0x5678,
                manufacturer="Gyro",
                product="E84",
            )

            result = await serial_port.connect_async()

            assert result is True
            assert serial_port.port == "COM16"
            assert open_calls == ["COM14", "COM16"]
        finally:
            serial_gyro.list_ports.comports = original_comports
            serial_gyro.serial_asyncio.open_serial_connection = original_open
            AsyncSerialPort._start_event_loop = original_start_event_loop

    asyncio.run(run_test())


def test_async_serial_connect_async_reuses_existing_background_tasks():
    async def run_test():
        original_start_event_loop = AsyncSerialPort._start_event_loop
        original_open = serial_gyro.serial_asyncio.open_serial_connection
        original_comports = serial_gyro.list_ports.comports

        port_entry = types.SimpleNamespace(
            device="COM14",
            serial_number="ABC123",
            location="1-1",
            vid=0x1234,
            pid=0x5678,
            manufacturer="Gyro",
            product="E84",
            interface=None,
        )

        async def fake_open_serial_connection(*, url, baudrate, bytesize, parity, stopbits):
            return DummyReader(), DummyWriter()

        AsyncSerialPort._start_event_loop = lambda self: None
        serial_gyro.serial_asyncio.open_serial_connection = fake_open_serial_connection
        serial_gyro.list_ports.comports = lambda: [port_entry]

        try:
            serial_port = AsyncSerialPort("COM14", auto_reconnect=True)
            loop = asyncio.get_running_loop()

            existing_reader_task = loop.create_future()
            existing_timeout_task = loop.create_future()
            existing_reconnect_task = loop.create_future()

            serial_port._reader_task = existing_reader_task
            serial_port._timeout_checker_task = existing_timeout_task
            serial_port._reconnect_task = existing_reconnect_task

            result = await serial_port.connect_async()

            assert result is True
            assert serial_port._reader_task is existing_reader_task
            assert serial_port._timeout_checker_task is existing_timeout_task
            assert serial_port._reconnect_task is existing_reconnect_task
        finally:
            serial_gyro.list_ports.comports = original_comports
            serial_gyro.serial_asyncio.open_serial_connection = original_open
            AsyncSerialPort._start_event_loop = original_start_event_loop

    asyncio.run(run_test())


def test_async_serial_read_async_marks_disconnected_on_eof():
    async def run_test():
        original_start_event_loop = AsyncSerialPort._start_event_loop

        AsyncSerialPort._start_event_loop = lambda self: None

        try:
            serial_port = AsyncSerialPort("COM14", auto_reconnect=False)
            serial_port._reader = EOFReader()
            serial_port._writer = DummyWriter()
            serial_port._state = ConnectionState.CONNECTED

            try:
                await serial_port.read_async(1)
                assert False, "Expected ConnectionError on EOF"
            except ConnectionError:
                pass

            assert serial_port._state == ConnectionState.DISCONNECTED
            assert serial_port._writer is None
        finally:
            AsyncSerialPort._start_event_loop = original_start_event_loop

    asyncio.run(run_test())
