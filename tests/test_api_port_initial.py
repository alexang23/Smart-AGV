import sys
import os
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from routers.port import api_port_initial


class DummyLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def make_request(loadport, e84, rfid=None, rfid_UHF=None):
    return types.SimpleNamespace(
        app=types.SimpleNamespace(
            state=types.SimpleNamespace(
                glogger=DummyLogger(),
                tsc=types.SimpleNamespace(loadport=loadport, e84=e84, rfid=rfid, rfid_UHF=rfid_UHF),
            )
        )
    )


def make_db(acc_type="USER", userid="tester", name="Tester"):
    login_user = types.SimpleNamespace(acc_type=acc_type, userid=userid, name=name)

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return login_user

    class DummyDB:
        def query(self, *args, **kwargs):
            return DummyQuery()

    return DummyDB()


def test_api_port_initial_runs_version_and_status_for_e84_ports():
    async def run_test():
        run_cmd_calls = []

        class DummyPort:
            def run_cmd(self, cmd):
                run_cmd_calls.append(cmd)

        request = make_request(
            loadport={1: {'enable': True, 'com': 'e84', 'id': 0, 'dual': 0, 'ver': 0}},
            e84={0: DummyPort()},
        )

        result = await api_port_initial(
            request=request,
            db=make_db(),
            login_id="1",
        )

        assert result["Success"] is True
        assert result["State"] == "OK"
        assert result["ErrorCode"] == 0
        assert result["Length"] == 1
        port = result["Loadports"][0]
        assert port["port_no"] == 1
        assert port["port_id"] == "LP1"
        assert port["enable"] is True
        assert port["type"] == "E84"
        assert port["dual"] == 0
        assert port["ver"] == 0
        assert run_cmd_calls == ["version", "status"]

    import asyncio
    asyncio.run(run_test())


def test_api_port_initial_rejects_all_permission_user():
    async def run_test():
        request = make_request(loadport={}, e84={})

        result = await api_port_initial(
            request=request,
            db=make_db(acc_type="ALL"),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 403

    import asyncio
    asyncio.run(run_test())


def test_api_port_initial_fails_when_e84_controller_is_none():
    async def run_test():
        request = make_request(
            loadport={1: {'enable': True, 'com': 'e84', 'id': 0, 'dual': 0, 'ver': 0}},
            e84={},
        )

        result = await api_port_initial(
            request=request,
            db=make_db(),
            login_id="1",
        )

        assert result["Success"] is False
        assert result["State"] == "NG"
        assert result["ErrorCode"] == 99
        assert result["Message"] == "E84 is None."

    import asyncio
    asyncio.run(run_test())


def test_api_port_initial_collects_non_e84_ports_without_commands():
    async def run_test():
        publish_calls = []

        class DummyRFID:
            def mqtt_publish_status(self, portno):
                publish_calls.append(portno)

        request = make_request(
            loadport={1: {'enable': True, 'com': 'RFID', 'id': 0, 'dual': 0, 'ver': 2}},
            e84={},
            rfid=DummyRFID(),
            rfid_UHF=DummyRFID(),
        )

        result = await api_port_initial(
            request=request,
            db=make_db(),
            login_id="1",
        )

        assert result["Success"] is True
        assert result["State"] == "OK"
        assert result["Length"] == 1
        port = result["Loadports"][0]
        assert port["type"] == "RFID"
        # RFID ports must not run E84 commands or publish status (trimmed scope)
        assert publish_calls == []

    import asyncio
    asyncio.run(run_test())


def test_api_port_initial_port_id_uses_settings_load_port_id(monkeypatch=None):
    async def run_test():
        from config import settings

        class DummyPort:
            def run_cmd(self, cmd):
                pass

        request = make_request(
            loadport={2: {'enable': True, 'com': 'e84', 'id': 0, 'dual': 0, 'ver': 1}},
            e84={0: DummyPort()},
        )

        original = settings.LOAD_PORT_2_ID
        settings.LOAD_PORT_2_ID = "LP2"
        try:
            result = await api_port_initial(
                request=request,
                db=make_db(),
                login_id="1",
            )
        finally:
            settings.LOAD_PORT_2_ID = original

        assert result["Loadports"][0]["port_id"] == "LP2"

    import asyncio
    asyncio.run(run_test())
