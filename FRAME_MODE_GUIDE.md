# AsyncSerialPort - FRAME 模式使用指南

## 📋 概述

AsyncSerialPort 現在支援兩種協議解析模式：

1. **LINE 模式** - 基於 `\r\n` 分隔符的文本協議（預設，保持向後兼容）
2. **FRAME 模式** - 基於 Header + Fixed Length + Checksum 的二進制協議（新增）

---

## 🎯 FRAME 模式特性

### 幀格式

預設幀結構：
```
[Header (2 bytes)] [Command ID (1 byte)] [Data (n bytes)] [Checksum (1 byte)]
```

範例（8 字節幀）：
```
0xAA 0x55 0x01 0x11 0x22 0x33 0x44 0xXX
 ^     ^    ^    ^    ^    ^    ^    ^
 |     |    |    |    |    |    |    |
 |     |    |    |    |    |    |    +-- Checksum: sum(前7字節) % 256
 |     |    |    |    |    |    +------- Data byte 4
 |     |    |    |    |    +------------ Data byte 3
 |     |    |    |    +----------------- Data byte 2
 |     |    |    +---------------------- Data byte 1
 |     |    +--------------------------- Command ID
 |     +-------------------------------- Header byte 2
 +------------------------------------- Header byte 1
```

### 核心功能

✅ **自動幀同步** - 自動搜尋幀頭標記（0xAA55）  
✅ **Checksum 驗證** - 自動驗證數據完整性  
✅ **緩衝區管理** - 自動處理不完整幀和無效數據  
✅ **錯誤恢復** - 丟棄無效幀，繼續尋找下一個有效幀  
✅ **溢出保護** - 防止緩衝區無限增長  

---

## 🚀 快速開始

### 基本使用

```python
import asyncio
from serial_gyro import AsyncSerialPort, ProtocolMode

async def main():
    # 創建 FRAME 模式實例
    serial = AsyncSerialPort(
        port="COM3",
        baudrate=9600,
        protocol_mode=ProtocolMode.FRAME,  # 使用 FRAME 模式
        frame_header=b'\xAA\x55',          # 幀頭標記
        frame_length=8,                     # 幀長度（字節）
        checksum_enabled=True,              # 啟用 Checksum 驗證
        max_buffer_size=256                 # 最大緩衝區大小
    )
    
    await serial.connect_async()
    
    # 構造一個幀
    frame = b'\xAA\x55\x01\x11\x22\x33\x44'
    checksum = sum(frame) % 256
    frame = frame + bytes([checksum])
    
    # 發送並等待回應
    response = await serial.send_command_async(
        command_id="CMD_01",
        data=frame,
        timeout=3.0
    )
    
    await serial.disconnect_async()

asyncio.run(main())
```

---

## 🔧 配置參數

### 初始化參數（FRAME 模式專用）

```python
AsyncSerialPort(
    # ... 基本串口參數 ...
    
    # FRAME 模式配置
    protocol_mode=ProtocolMode.FRAME,      # 協議模式
    frame_header=b'\xAA\x55',              # 幀頭標記（可自定義）
    frame_length=8,                         # 固定幀長度
    checksum_enabled=True,                  # 是否啟用 Checksum
    max_buffer_size=256,                    # 讀取緩衝區最大大小
    
    # 自定義解析器（可選）
    response_parser=custom_frame_parser    # 自定義幀解析函數
)
```

### 參數說明

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `protocol_mode` | ProtocolMode | LINE | 協議模式（LINE/FRAME） |
| `frame_header` | bytes | b'\xAA\x55' | 幀頭標記 |
| `frame_length` | int | 8 | 固定幀長度（字節） |
| `checksum_enabled` | bool | True | 是否驗證 Checksum |
| `max_buffer_size` | int | 256 | 緩衝區最大大小 |

---

## 📝 自定義解析器

### 預設解析器

預設假設幀格式：
```
[Header(2)] [CMD_ID(1)] [Data(...)] [Checksum(1)]
```

Command ID 提取自第 3 個字節。

### 自定義解析器範例

```python
def custom_frame_parser(frame: bytes):
    """
    自定義幀解析器
    
    Args:
        frame: 完整的幀數據（已驗證 Checksum）
        
    Returns:
        Tuple[Optional[str], bytes]: (command_id, frame_data)
    """
    if len(frame) >= 8:
        # 提取 Command ID（第 3 字節）
        cmd_id = f"CMD_{frame[2]:02X}"
        
        # 提取數據部分（bytes 3-6）
        data = frame[3:7]
        
        return cmd_id, data
    
    return None, frame

# 使用自定義解析器
serial = AsyncSerialPort(
    port="COM3",
    protocol_mode=ProtocolMode.FRAME,
    response_parser=custom_frame_parser
)
```

### 複雜協議範例

```python
def advanced_frame_parser(frame: bytes):
    """
    進階幀解析器
    
    幀格式: [0xAA, 0x55, Type, ID, Seq, Data1, Data2, Checksum]
    """
    if len(frame) != 8:
        return None, frame
    
    frame_type = frame[2]  # 幀類型
    frame_id = frame[3]    # 幀 ID
    sequence = frame[4]     # 序列號
    
    # 組合 command_id
    cmd_id = f"TYPE_{frame_type:02X}_ID_{frame_id:02X}_SEQ_{sequence:02X}"
    
    # 提取數據
    data = frame[5:7]
    
    return cmd_id, data
```

---

## 🔍 Checksum 驗證

### 預設 Checksum 算法

```python
checksum = sum(frame[:-1]) % 256
```

即：所有字節（除了最後一個 Checksum 字節）的和取模 256。

### 自定義 Checksum

如果需要不同的 Checksum 算法，可以繼承 `AsyncSerialPort` 並覆寫 `_validate_checksum` 方法：

```python
class CustomSerialPort(AsyncSerialPort):
    def _validate_checksum(self, frame: bytes) -> bool:
        """自定義 Checksum 驗證"""
        if len(frame) < 2:
            return False
        
        # 範例：CRC8 算法
        crc = 0
        for byte in frame[:-1]:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        
        return crc == frame[-1]

# 使用自定義類別
serial = CustomSerialPort(
    port="COM3",
    protocol_mode=ProtocolMode.FRAME
)
```

---

## 📊 幀處理流程

### 接收流程

```
1. 從串口讀取數據（每次最多 64 bytes）
   ↓
2. 累積到讀取緩衝區
   ↓
3. 在緩衝區中搜尋幀頭標記（0xAA55）
   ↓
4. 找到幀頭後，檢查是否有完整幀（根據 frame_length）
   ↓
5. 提取完整幀
   ↓
6. 驗證 Checksum
   ↓
7a. Checksum 有效 → 返回幀，匹配 Command ID
7b. Checksum 無效 → 記錄錯誤，跳過 2 字節繼續搜尋
```

### 錯誤處理

| 情況 | 處理方式 | 日誌級別 |
|------|----------|----------|
| 找不到幀頭 | 丟棄部分數據，保留最後幾個字節 | DEBUG |
| 幀頭前有雜訊 | 丟棄幀頭前的所有數據 | DEBUG |
| Checksum 錯誤 | 丟棄該幀，跳過 2 字節繼續搜尋 | WARNING |
| 緩衝區溢出 | 清理舊數據，保留最後一個幀長度的數據 | WARNING |

---

## 🛠️ 輔助工具

### 幀構造輔助函數

```python
def create_frame(cmd_id: int, data: bytes, 
                 header: bytes = b'\xAA\x55') -> bytes:
    """
    構造標準幀
    
    Args:
        cmd_id: 命令 ID (0-255)
        data: 數據部分（4 bytes）
        header: 幀頭（預設 0xAA55）
        
    Returns:
        bytes: 完整的幀（包含 Checksum）
    """
    if len(data) != 4:
        raise ValueError("Data must be 4 bytes")
    
    frame = header + bytes([cmd_id]) + data
    checksum = sum(frame) % 256
    return frame + bytes([checksum])

# 使用範例
frame = create_frame(0x01, bytes([0x11, 0x22, 0x33, 0x44]))
print(f"Frame: {frame.hex()}")  # Frame: aa55011122334400
```

### 幀解析輔助函數

```python
def parse_frame(frame: bytes) -> tuple:
    """
    解析標準幀
    
    Returns:
        Tuple[int, bytes]: (cmd_id, data) 或 None
    """
    if len(frame) != 8:
        return None
    
    if frame[0:2] != b'\xAA\x55':
        return None
    
    # 驗證 Checksum
    checksum_calc = sum(frame[:7]) % 256
    if checksum_calc != frame[7]:
        return None
    
    cmd_id = frame[2]
    data = frame[3:7]
    return cmd_id, data

# 使用範例
result = parse_frame(frame)
if result:
    cmd_id, data = result
    print(f"CMD: 0x{cmd_id:02X}, Data: {data.hex()}")
```

---

## 📈 使用範例

### 範例 1: 簡單命令

```python
async def send_simple_command():
    serial = AsyncSerialPort(
        port="COM3",
        protocol_mode=ProtocolMode.FRAME,
        frame_length=8
    )
    
    await serial.connect_async()
    
    # 構造幀: [0xAA, 0x55, 0x01, 0x00, 0x00, 0x00, 0x00, checksum]
    frame = b'\xAA\x55\x01\x00\x00\x00\x00'
    checksum = sum(frame) % 256
    frame = frame + bytes([checksum])
    
    response = await serial.send_command_async("CMD_01", frame)
    print(f"Response: {response.hex()}")
    
    await serial.disconnect_async()
```

### 範例 2: 並發多個命令

```python
async def send_multiple_commands():
    serial = AsyncSerialPort(
        port="COM3",
        protocol_mode=ProtocolMode.FRAME,
        frame_length=8
    )
    
    await serial.connect_async()
    
    # 創建多個幀
    frames = []
    for i in range(5):
        frame = b'\xAA\x55' + bytes([i, 0x11*i, 0x22*i, 0x33*i, 0x44*i])
        checksum = sum(frame) % 256
        frames.append(frame + bytes([checksum]))
    
    # 並發發送
    tasks = [
        serial.send_command_async(f"CMD_{i:02X}", frames[i])
        for i in range(5)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    for i, resp in enumerate(responses):
        print(f"Response {i}: {resp.hex()}")
    
    await serial.disconnect_async()
```

### 範例 3: LINE 和 FRAME 模式切換

```python
async def dual_mode_example():
    # LINE 模式串口
    serial_line = AsyncSerialPort(
        port="COM3",
        protocol_mode=ProtocolMode.LINE
    )
    
    # FRAME 模式串口
    serial_frame = AsyncSerialPort(
        port="COM4",
        protocol_mode=ProtocolMode.FRAME,
        frame_length=8
    )
    
    await serial_line.connect_async()
    await serial_frame.connect_async()
    
    # LINE 模式通訊
    resp1 = await serial_line.send_command_async(
        "STATUS", 
        b"GET_STATUS\r\n"
    )
    
    # FRAME 模式通訊
    frame = create_frame(0x01, bytes([0x11, 0x22, 0x33, 0x44]))
    resp2 = await serial_frame.send_command_async(
        "CMD_01",
        frame
    )
    
    await serial_line.disconnect_async()
    await serial_frame.disconnect_async()
```

---

## 🐛 故障排除

### 常見問題

#### 1. 無法接收到回應

**可能原因**：
- 幀頭標記不匹配
- 幀長度配置錯誤
- Checksum 計算錯誤

**解決方法**：
```python
# 啟用 DEBUG 日誌查看詳細信息
logging.basicConfig(level=logging.DEBUG)

# 檢查實際接收的數據
serial._logger.setLevel(logging.DEBUG)
```

#### 2. Checksum 驗證失敗

**檢查方法**：
```python
# 手動驗證 Checksum
frame = b'\xAA\x55\x01\x11\x22\x33\x44\x00'
checksum = sum(frame[:7]) % 256
print(f"Expected checksum: 0x{checksum:02X}")
print(f"Actual checksum: 0x{frame[7]:02X}")
```

#### 3. 緩衝區溢出

**原因**：接收速度 > 處理速度

**解決方法**：
```python
# 增大緩衝區
serial = AsyncSerialPort(
    port="COM3",
    protocol_mode=ProtocolMode.FRAME,
    max_buffer_size=512  # 增大到 512 bytes
)
```

---

## 📚 API 參考

### ProtocolMode 枚舉

```python
class ProtocolMode(Enum):
    LINE = "line"      # 行分隔符模式
    FRAME = "frame"    # 幀格式模式
```

### 新增方法

#### `_read_frame_async()`
從緩衝區讀取並解析一個完整的幀。

#### `_validate_checksum(frame: bytes) -> bool`
驗證幀的 Checksum。

#### `_default_frame_parser(frame: bytes) -> Tuple[Optional[str], bytes]`
預設幀解析器。

---

## ⚡ 性能考慮

- **緩衝區大小**：根據數據速率調整 `max_buffer_size`
- **幀長度**：較短的幀可以更快檢測錯誤
- **Checksum**：如果數據可靠，可以關閉 Checksum 以提升性能

---

## 🔄 向後兼容性

✅ 完全兼容現有 LINE 模式代碼  
✅ 預設使用 LINE 模式  
✅ 所有現有 API 保持不變  
✅ 可以同時使用兩種模式（不同實例）  

---

**更多信息請參考主文檔 README_SERIAL.md**
