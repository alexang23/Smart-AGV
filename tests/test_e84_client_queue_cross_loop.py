import asyncio
from threading import Thread
import types

# If pytest isn't installed in the environment (common in CI-less dev), provide a minimal fallback
try:
    import pytest
except Exception:
    pytest = types.SimpleNamespace(mark=types.SimpleNamespace(asyncio=lambda f: f))

from e84_client import E84Client, E84Event, E84Message, E84MessageType, E84Signal


@pytest.mark.asyncio
async def test_put_from_different_loop_thread():
    """模擬在另一個 thread/loop 中呼叫 handler，驗證事件能被安全放入主 loop 的佇列"""
    client = E84Client(port="COM_TEST", RF_port="RF", event_queue_size=5)

    # 在目前測試 loop 建立 queue 並記錄該 loop（模擬 connect_async 行為）
    client._event_queue = asyncio.Queue(maxsize=5)
    client._event_queue_loop = asyncio.get_running_loop()

    # 建一個簡單的 sensor message（70 系列）
    message = E84Message(E84MessageType.READ, command=0x70, data=0x0002)

    exceptions = []

    def thread_target():
        try:
            # 這會在新的事件迴圈執行，模擬不同的 loop/thread
            asyncio.run(client._handle_sensor_event(message))
        except Exception as e:  # pragma: no cover - 捕獲任何非預期例外
            exceptions.append(e)

    t = Thread(target=thread_target)
    t.start()
    t.join(timeout=2)

    assert not exceptions, f"Handler in other thread raised: {exceptions}"

    # 從主 loop 讀取事件
    ev = await asyncio.wait_for(client.get_event(), timeout=1.0)
    assert isinstance(ev, E84Event)
    assert ev.series == 0x70
    assert ev.signal_name == E84Signal.get_signal_name(message.data & 0xFF)


@pytest.mark.asyncio
async def test_put_from_same_loop():
    """確保在相同 loop 中直接 await handler 也能正常運作"""
    client = E84Client(port="COM_TEST", RF_port="RF", event_queue_size=5)
    client._event_queue = asyncio.Queue(maxsize=5)
    client._event_queue_loop = asyncio.get_running_loop()

    message = E84Message(E84MessageType.READ, command=0x70, data=0x0004)

    # 直接在同一個 loop 中呼叫
    await client._handle_sensor_event(message)

    ev = await asyncio.wait_for(client.get_event(), timeout=1.0)
    assert isinstance(ev, E84Event)
    assert ev.series == 0x70
    assert ev.signal_name == E84Signal.get_signal_name(message.data & 0xFF)


@pytest.mark.asyncio
async def test_wait_for_signal_creates_queue_and_cross_loop_put():
    """模擬 `_wait_for_signal` 先建立佇列，另一個 loop/thread 放事件進來的情況，確認不會拋出 RuntimeError"""
    client = E84Client(port="COM_TEST", RF_port="RF", event_queue_size=5)

    # 啟動 _wait_for_signal 為背景任務，讓它在當前 loop 建立 queue
    waiter = asyncio.create_task(client._wait_for_signal("VALID", expected_state=True, timeout=0.5))

    # 等一下讓 waiter 執行，建立 queue
    await asyncio.sleep(0.05)

    # 確認 queue 已建立且記錄了所屬 loop
    assert client._event_queue is not None
    assert client._event_queue_loop is not None

    # 建一個簡單的 sensor message（70 系列）
    message = E84Message(E84MessageType.READ, command=0x70, data=0x0002)

    exceptions = []

    def thread_target():
        try:
            # 在另一個 loop 中執行 handler，模擬跨 loop put
            asyncio.run(client._handle_sensor_event(message))
        except Exception as e:  # pragma: no cover - 捕獲任何非預期例外
            exceptions.append(e)

    from threading import Thread
    t = Thread(target=thread_target)
    t.start()
    t.join(timeout=2)

    assert not exceptions, f"跨 loop handler raised exceptions: {exceptions}"

    # 從主 loop 讀取事件
    ev = await asyncio.wait_for(client.get_event(), timeout=1.0)
    assert isinstance(ev, E84Event)
    assert ev.series == 0x70
    assert ev.signal_name == E84Signal.get_signal_name(message.data & 0xFF)

    # 清理 waiter
    try:
        waiter.cancel()
    except Exception:
        pass
