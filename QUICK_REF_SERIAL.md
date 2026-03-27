# AsyncSerialPort 快速參考

## 🚀 快速開始

### 最簡單的使用方式

```python
import asyncio
from serial_gyro import AsyncSerialPort

# Async 方式
async def main():
    async with AsyncSerialPort("COM3", baudrate=9600) as serial:
        response = await serial.send_command_async(
            "CMD_001", 
            b"GET_STATUS\r\n"
        )
        print(response)

asyncio.run(main())
```

```python
# Sync 方式
from serial_gyro import AsyncSerialPort

with AsyncSerialPort("COM3", baudrate=9600) as serial:
    response = serial.send_command("CMD_001", b"GET_STATUS\r\n")
    print(response)
```

---

## 📋 常用 API

### 初始化
```python
serial = AsyncSerialPort(
    port="COM3",              # 串口名稱
    baudrate=9600,            # 波特率
    auto_reconnect=True,      # 自動重連
    response_timeout=5.0      # 回應超時
)
```

### 連線/斷線
```python
# Async
await serial.connect_async()
await serial.disconnect_async()

# Sync
serial.connect()
serial.disconnect()
```

### 發送命令
```python
# Async - 等待回應
response = await serial.send_command_async(
    command_id="CMD_001",
    data=b"GET_STATUS\r\n",
    timeout=3.0
)

# Async - 不等回應
await serial.send_command_async(
    "CMD_002",
    b"PING\r\n",
    expect_response=False
)

# Sync - 等待回應
response = serial.send_command(
    "CMD_003",
    b"GET_DATA\r\n"
)
```

### 基礎讀寫
```python
# Async
await serial.write_async(b"data")
data = await serial.read_async(100)
line = await serial.readline_async()

# Sync
serial.write(b"data")
data = serial.read(100)
line = serial.readline()
```

### 並發命令
```python
# 同時發送多個命令
tasks = [
    serial.send_command_async("A", b"CMD_A\r\n"),
    serial.send_command_async("B", b"CMD_B\r\n"),
    serial.send_command_async("C", b"CMD_C\r\n"),
]
responses = await asyncio.gather(*tasks)
```

### 統計資訊
```python
# 基本統計
stats = serial.statistics
print(f"發送: {stats['commands_sent']}")
print(f"接收: {stats['responses_received']}")
print(f"超時: {stats['timeouts']}")

# 回應時間
serial.print_response_time_stats()
rt_stats = serial.get_response_time_stats()
print(f"平均: {rt_stats['avg_ms']:.2f} ms")
```

### 屬性
```python
serial.is_connected    # bool: 是否連線
serial.state          # ConnectionState: 連線狀態
serial.statistics     # dict: 統計資訊
```

---

## 🔧 自定義協議

### 預設格式
```
RESPONSE:command_id:data\r\n
```

### 自定義解析器
```python
def my_parser(response: bytes):
    """
    解析您的協議格式
    返回: (command_id, data)
    """
    # 範例: JSON 格式
    import json
    data = json.loads(response)
    return data.get("cmd_id"), response
    
    # 範例: 固定格式 "ID:DATA"
    parts = response.split(b':', 1)
    return parts[0].decode(), parts[1]

serial = AsyncSerialPort(
    port="COM3",
    response_parser=my_parser
)
```

---

## 🎯 實際場景範例

### 場景：AGV 控制
```python
async def agv_control():
    serial = AsyncSerialPort("COM3", baudrate=9600)
    serial.connect()
    
    # 背景：高頻率狀態更新 (async)
    async def background():
        while serial.is_connected:
            await serial.send_command_async(
                f"STATUS_{time.time()}",
                b"HEARTBEAT\r\n",
                expect_response=False
            )
            await asyncio.sleep(0.5)
    
    task = asyncio.create_task(background())
    
    # 主程序：關鍵命令 (sync)
    position = serial.send_command(
        "GET_POS",
        b"GET_POSITION\r\n",
        timeout=2.0
    )
    print(f"位置: {position}")
    
    task.cancel()
    serial.disconnect()
```

---

## 🔔 事件回調

```python
serial = AsyncSerialPort(
    port="COM3",
    on_connected=lambda: print("✅ 連線"),
    on_disconnected=lambda: print("❌ 斷線"),
    on_reconnecting=lambda: print("🔄 重連中")
)
```

---

## ⚠️ 錯誤處理

```python
try:
    response = await serial.send_command_async(
        "CMD", b"DATA\r\n", timeout=3.0
    )
except TimeoutError:
    print("超時")
except ConnectionError:
    print("連線錯誤")
except ValueError:
    print("命令 ID 重複")
```

---

## 📊 回應時間分級

| 時間範圍 | 級別 | Log Level |
|---------|------|-----------|
| < 100ms | FAST | DEBUG |
| 100-500ms | NORMAL | INFO |
| 500ms-2s | SLOW | WARNING |
| > 2s | VERY SLOW | WARNING |

---

## 💡 提示

1. **命令 ID 唯一**: 每個待處理命令需要不同的 ID
2. **協議適配**: 根據設備修改 `response_parser`
3. **Context Manager**: 推薦使用 `with`/`async with` 自動清理
4. **混合使用**: Async 和 Sync 可以同時使用
5. **日誌級別**: 設置 `logging.DEBUG` 查看詳細信息

---

## 📁 相關文件

- `serial_gyro.py` - 類別實作
- `test_serial.py` - 簡單測試
- `serial_example.py` - 完整範例
- `README_SERIAL.md` - 詳細文檔

---

**更多詳情請參考 README_SERIAL.md**
