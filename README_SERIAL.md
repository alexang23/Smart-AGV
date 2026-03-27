# AsyncSerialPort - 串口通訊類別

## 📋 功能特點

✅ **雙介面支援**: 同時支援 Async 和 Sync API  
✅ **自動重連**: 檢測斷線並自動嘗試重連  
✅ **命令匹配**: 自動匹配命令和回應，支援並發命令  
✅ **回應時間追蹤**: 記錄每個命令的回應時間並生成統計報告  
✅ **事件回調**: 提供連線、斷線、重連等事件回調  
✅ **Context Manager**: 支援 `async with` 和 `with` 語法  
✅ **靈活協議**: 可自定義協議解析器適配不同設備  

---

## 🚀 快速開始

### 安裝依賴

```bash
pip install pyserial pyserial-asyncio
```

或使用 pipenv:

```bash
pipenv install pyserial pyserial-asyncio
```

### 基本使用

#### Async 方式（推薦）

```python
import asyncio
from serial_gyro import AsyncSerialPort

async def main():
    # 創建串口實例
    serial = AsyncSerialPort(
        port="COM3",          # Windows: COM3, Linux: /dev/ttyUSB0
        baudrate=9600,
        auto_reconnect=True
    )
    
    # 連線
    await serial.connect_async()
    
    # 發送命令並等待回應
    response = await serial.send_command_async(
        command_id="CMD_001",
        data=b"GET_STATUS\r\n",
        timeout=3.0
    )
    print(f"回應: {response}")
    
    # 斷線
    await serial.disconnect_async()

asyncio.run(main())
```

#### Sync 方式

```python
from serial_gyro import AsyncSerialPort

# 創建串口實例
serial = AsyncSerialPort(port="COM3", baudrate=9600)

# 連線
serial.connect()

# 發送命令並等待回應
response = serial.send_command(
    command_id="CMD_001",
    data=b"GET_STATUS\r\n"
)
print(f"回應: {response}")

# 斷線
serial.disconnect()
```

#### Context Manager

```python
# Async Context Manager
async with AsyncSerialPort("COM3", baudrate=9600) as serial:
    response = await serial.send_command_async("CMD_001", b"GET_STATUS\r\n")

# Sync Context Manager
with AsyncSerialPort("COM3", baudrate=9600) as serial:
    response = serial.send_command("CMD_001", b"GET_STATUS\r\n")
```

---

## 📖 詳細說明

### 初始化參數

```python
AsyncSerialPort(
    port="COM3",                    # 串口名稱
    baudrate=9600,                  # 波特率
    bytesize=8,                     # 數據位 (5, 6, 7, 8)
    parity='N',                     # 校驗位 ('N', 'E', 'O', 'M', 'S')
    stopbits=1,                     # 停止位 (1, 1.5, 2)
    timeout=1.0,                    # 讀取超時（秒）
    write_timeout=1.0,              # 寫入超時（秒）
    
    # 自動重連設定
    auto_reconnect=True,            # 是否自動重連
    reconnect_interval=2.0,         # 重連間隔（秒）
    max_reconnect_attempts=-1,      # 最大重連次數（-1 = 無限）
    
    # 命令回應設定
    response_timeout=5.0,           # 命令回應超時（秒）
    
    # 事件回調
    on_connected=callback_func,     # 連線成功回調
    on_disconnected=callback_func,  # 斷線回調
    on_reconnecting=callback_func,  # 重連中回調
    
    # 協議解析器
    response_parser=parser_func     # 自定義回應解析器
)
```

### 主要方法

#### 連線管理

```python
# Async
await serial.connect_async()
await serial.disconnect_async()

# Sync
serial.connect()
serial.disconnect()
```

#### 基礎 I/O

```python
# Async 寫入/讀取
await serial.write_async(b"data")
data = await serial.read_async(100)
line = await serial.readline_async()

# Sync 寫入/讀取
serial.write(b"data")
data = serial.read(100)
line = serial.readline()
```

#### 命令-回應匹配

```python
# Async
response = await serial.send_command_async(
    command_id="CMD_001",       # 唯一命令 ID
    data=b"GET_STATUS\r\n",     # 要發送的數據
    timeout=3.0,                # 超時時間（可選）
    expect_response=True        # 是否等待回應（可選）
)

# Sync
response = serial.send_command(
    command_id="CMD_001",
    data=b"GET_STATUS\r\n",
    timeout=3.0
)
```

#### 並發命令

```python
# 同時發送多個命令，自動匹配各自的回應
tasks = [
    serial.send_command_async("CMD_001", b"GET_POS\r\n"),
    serial.send_command_async("CMD_002", b"GET_SPEED\r\n"),
    serial.send_command_async("CMD_003", b"GET_BATTERY\r\n"),
]
responses = await asyncio.gather(*tasks)
```

### 統計資訊

```python
# 獲取基本統計
stats = serial.statistics
print(f"發送字節: {stats['bytes_sent']}")
print(f"接收字節: {stats['bytes_received']}")
print(f"發送命令: {stats['commands_sent']}")
print(f"超時次數: {stats['timeouts']}")

# 獲取回應時間統計
rt_stats = serial.get_response_time_stats()
print(f"平均回應時間: {rt_stats['avg_ms']:.2f} ms")

# 打印完整統計報告
serial.print_response_time_stats()
```

### 屬性

```python
serial.is_connected      # 是否已連線
serial.state             # 連線狀態 (ConnectionState 枚舉)
serial.statistics        # 統計資訊字典
```

---

## 🔧 自定義協議解析器

預設的協議格式為: `RESPONSE:command_id:data\r\n`

如果您的設備使用不同的協議，可以提供自定義解析器：

```python
def custom_parser(response: bytes) -> Tuple[Optional[str], bytes]:
    """
    自定義協議解析器
    
    Args:
        response: 從串口接收的原始數據
        
    Returns:
        Tuple[Optional[str], bytes]: (command_id, response_data)
        - command_id: 命令 ID（None 表示無法識別）
        - response_data: 回應數據
    """
    # 範例 1: JSON 格式
    import json
    try:
        data = json.loads(response.decode('utf-8'))
        cmd_id = data.get("cmd_id")
        return cmd_id, response
    except:
        return None, response
    
    # 範例 2: 固定格式 "CMD_ID:DATA"
    try:
        parts = response.split(b':', 1)
        if len(parts) == 2:
            cmd_id = parts[0].decode('utf-8')
            return cmd_id, parts[1]
    except:
        pass
    
    return None, response

# 使用自定義解析器
serial = AsyncSerialPort(
    port="COM3",
    baudrate=9600,
    response_parser=custom_parser
)
```

---

## 📊 回應時間統計

每個命令的回應時間都會自動記錄並分類：

```python
# 發送一些命令
for i in range(100):
    await serial.send_command_async(f"CMD_{i}", b"GET_DATA\r\n")

# 查看統計報告
serial.print_response_time_stats()
```

輸出範例：

```
==================================================
Response Time Statistics
==================================================
Total Commands:  100
Min Time:        12.34 ms
Max Time:        234.56 ms
Average Time:    56.78 ms
Last Time:       45.23 ms

Distribution:
  0-100ms      :   80 ( 80.0%) ████████████████████████████████████████
  100-500ms    :   18 ( 18.0%) █████████
  500ms-1s     :    2 (  2.0%) █
  1s-2s        :    0 (  0.0%) 
  2s+          :    0 (  0.0%) 
==================================================
```

Log 輸出會根據回應時間自動分級：
- `[FAST]` (< 100ms): DEBUG level
- `[NORMAL]` (100-500ms): INFO level
- `[SLOW]` (500ms-2s): WARNING level
- `[VERY SLOW]` (> 2s): WARNING level

---

## 🔄 自動重連

當檢測到連線中斷時，會自動嘗試重連：

```python
serial = AsyncSerialPort(
    port="COM3",
    baudrate=9600,
    auto_reconnect=True,            # 啟用自動重連
    reconnect_interval=2.0,         # 每 2 秒重試一次
    max_reconnect_attempts=10,      # 最多重試 10 次（-1 = 無限）
    on_reconnecting=lambda: print("正在重連...")
)
```

重連期間：
- 待處理的命令會保持等待
- 新的命令會拋出 `ConnectionError`
- 重連成功後會觸發 `on_connected` 回調

---

## 💡 實際應用範例

### AGV 控制場景

```python
async def agv_control():
    """
    實際場景：
    - 大部分命令使用 async（高頻率狀態更新）
    - 關鍵命令使用 sync（需要立即回應）
    """
    serial = AsyncSerialPort(
        port="COM3",
        baudrate=9600,
        auto_reconnect=True
    )
    
    serial.connect()
    
    # 背景任務：持續發送狀態（async）
    async def status_updater():
        count = 0
        while serial.is_connected:
            await serial.send_command_async(
                f"STATUS_{count:04d}",
                b"HEARTBEAT\r\n",
                expect_response=False
            )
            count += 1
            await asyncio.sleep(0.5)
    
    # 啟動背景任務
    task = asyncio.create_task(status_updater())
    
    # 主程序：定期獲取關鍵信息（sync）
    for i in range(10):
        await asyncio.sleep(2)
        
        # 使用 sync 獲取位置（阻塞直到收到回應）
        try:
            position = serial.send_command(
                f"GET_POS_{i}",
                b"GET_POSITION\r\n",
                timeout=2.0
            )
            print(f"位置: {position}")
        except TimeoutError:
            print("位置查詢超時")
    
    # 清理
    task.cancel()
    serial.disconnect()
```

---

## 🐛 錯誤處理

```python
try:
    response = await serial.send_command_async(
        "CMD_001",
        b"GET_DATA\r\n",
        timeout=3.0
    )
except TimeoutError:
    # 超時未收到回應
    print("命令超時")
except ConnectionError:
    # 串口未連線或連線中斷
    print("連線錯誤")
except ValueError:
    # 重複的 command_id
    print("命令 ID 重複")
```

---

## 📝 注意事項

1. **Command ID 唯一性**: 每個待處理的命令必須有唯一的 `command_id`
2. **協議解析器**: 必須根據實際設備協議實作或提供自定義 `response_parser`
3. **線程安全**: Async 和 Sync API 可以混合使用，內部已處理線程安全
4. **資源清理**: 使用 Context Manager 或確保調用 `disconnect()` 來清理資源
5. **背景線程**: 實例會創建背景線程運行事件循環，在 `disconnect()` 時停止

---

## 📂 文件說明

- `serial_gyro.py` - AsyncSerialPort 類別實作
- `serial_example.py` - 詳細使用範例（11 個不同場景）
- `test_serial.py` - 簡單測試程序
- `README_SERIAL.md` - 本文檔

---

## 🧪 測試

運行簡單測試：

```bash
python test_serial.py
```

查看所有範例：

```bash
python serial_example.py
```

（範例文件中的各個範例需要取消註解才會執行）

---

## 📄 授權

此代碼為項目內部使用，請根據項目需求調整。

---

## 🤝 貢獻

如有問題或建議，請聯繫開發團隊。

---

**祝您使用愉快！** 🚀
