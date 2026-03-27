# E84 Protocol Implementation - AGV 通訊協議

## 📋 概述

E84 是 SEMI (Semiconductor Equipment and Materials International) 定義的設備間通訊協議，用於 AGV（自動導引車）與設備之間的 Load/Unload 操作。

本實作提供完整的 E84 協議支援，包括：
- ✅ 訊息解析與建構
- ✅ Checksum 驗證
- ✅ 命令/回應配對
- ✅ 事件處理（Callbacks + Queue）
- ✅ 完整的 Load/Unload 自動流程
- ✅ Timeout 參數管理（TA1-TA16）

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

```python
import asyncio
from e84 import E84Client

async def main():
    # 創建 E84 客戶端
    async with E84Client("COM3", baudrate=9600) as e84:
        # 初始化 Timeout 參數
        await e84.initialize_timeout_params()
        
        # 執行 Load 流程
        success = await e84.load_async()
        if success:
            print("✅ Load 完成")
        else:
            print("❌ Load 失敗")

asyncio.run(main())
```

---

## 📖 協議說明

### 訊息格式

#### WRITE 訊息（AGV → 設備）
```
格式: 55 AA [CMD_H] [CMD_L] [PARAM_H] [PARAM_L] [CHECKSUM]
長度: 7 bytes

範例: 55 AA 80 01 00 01 81
     ├─┬─┘ ├──┬──┘ ├───┬──┘ └─ Checksum
     │ │    │  │    │   └─ 參數低位元組 (0x01)
     │ │    │  │    └─ 參數高位元組 (0x00)
     │ │    │  └─ 命令低位元組 (0x01)
     │ │    └─ 命令高位元組 (0x80)
     │ └─ Header (固定)
     └─ Header (固定)
```

#### READ 訊息（設備 → AGV）
```
格式: AA 55 [CMD_H] [CMD_L] [DATA_H] [DATA_L] [STATUS] [CHECKSUM]
長度: 8 bytes

範例: AA 55 80 01 00 01 00 81
     ├─┬─┘ ├──┬──┘ ├───┬──┘ ├┘ └─ Checksum
     │ │    │  │    │   │   │   └─ 狀態位元組
     │ │    │  │    │   │   └─ 資料低位元組
     │ │    │  │    │   └─ 資料高位元組
     │ │    │  │    └─ 命令 (回應對應的命令)
     │ │    │  └─ 命令低位元組
     │ │    └─ 命令高位元組
     │ └─ Header (固定)
     └─ Header (固定)
```

### Checksum 計算

採用簡單累加 modulo 256：

```python
checksum = sum(message_bytes) & 0xFF
```

### 命令系列

| 系列 | 代碼範圍 | 說明 |
|------|---------|------|
| 讀取 | 0x00xx | 讀取配置、狀態 |
| 寫入 | 0x80xx | 設定參數、控制命令 |
| 感測器事件 | 0x0070 | 感測器狀態變化通知 |
| 狀態事件 | 0x0071 | 設備狀態變化通知 |
| 警報事件 | 0x0080 | E84 警報通知 |

---

## 🎯 主要功能

### 1. E84Client 類別

繼承自 `AsyncSerialPort`，提供完整的 E84 功能。

#### 初始化參數

```python
E84Client(
    port: str,                              # 串口名稱
    baudrate: int = 9600,                   # 波特率
    on_sensor_event: Callable = None,       # 感測器事件回調
    on_state_event: Callable = None,        # 狀態事件回調
    event_queue_size: int = None,           # 事件佇列大小
    default_ta_params: Dict = None,         # 自定義 TA 參數
    **kwargs                                # 其他 AsyncSerialPort 參數
)
```

### 2. 基本命令

```python
# 讀取韌體版本
version = await e84.read_firmware_version()
print(f"版本: {version[0]}.{version[1]}")

# 初始化 Timeout 參數
await e84.initialize_timeout_params()

# 設定單個 TA 參數
await e84.set_timeout_param(1, 0x05)  # TA1 = 0.5 秒

# DB25 Port 控制
await e84.db25_port_control(open=True)

# SELECT 控制
await e84.select_control(select_on=True)

# 發送 LOAD/UNLOAD 命令
await e84.send_load_command()
await e84.send_unload_command()

# 手臂回收完成
await e84.arm_back_complete()

# Alarm Reset
await e84.alarm_reset()
```

### 3. 完整流程

#### Load 流程

```python
# 全自動 Load 流程
success = await e84.load_async(timeout_per_step=15.0)
```

流程步驟：
1. DB25 Port Open
2. SELECT ON
3. SELECT OFF
4. 發送 LOAD 命令
5. 等待訊號序列（VALID → CS_0 → L_REQ → TR_REQ → READY → BUSY）
6. 等待 L_REQ OFF（可伸出手臂放貨）
7. 通知手臂回收完成
8. 等待完成訊號序列
9. Alarm Reset

#### Unload 流程

```python
# 全自動 Unload 流程
success = await e84.unload_async(timeout_per_step=15.0)
```

流程與 Load 類似，但使用 U_REQ 而非 L_REQ。

### 4. 事件處理

#### 方式 1: Callbacks（即時通知）

```python
def on_sensor(signal: str, state: bool):
    print(f"訊號 {signal}: {'ON' if state else 'OFF'}")

def on_state(code: int, description: str):
    print(f"狀態: {description}")

e84 = E84Client(
    "COM3",
    on_sensor_event=on_sensor,
    on_state_event=on_state
)
```

**優點**：
- 即時響應
- 實現簡單
- 適合日誌記錄和簡單監控

#### 方式 2: Event Queue（複雜處理）

```python
e84 = E84Client("COM3", event_queue_size=100)

# 啟動事件處理器
async def event_handler():
    while True:
        event = await e84.get_event(timeout=5.0)
        print(f"事件: {event.signal_name} = {event.description}")

asyncio.create_task(event_handler())
```

**優點**：
- 事件順序保證
- 不阻塞主流程
- 適合複雜狀態機

#### 方式 3: Hybrid（推薦）

```python
def quick_log(signal: str, state: bool):
    logging.info(f"{signal}: {state}")

e84 = E84Client(
    "COM3",
    on_sensor_event=quick_log,      # Callback 即時記錄
    event_queue_size=100             # Queue 處理複雜邏輯
)
```

**優點**：
- 兼具即時性和靈活性
- Callback 用於監控，Queue 用於業務邏輯
- 最適合生產環境

---

## 📊 訊號說明

### E84 感測器訊號（70 系列事件）

| 訊號 | ON 代碼 | OFF 代碼 | 說明 |
|------|---------|----------|------|
| GO | 0x00 | 0x01 | GO 訊號 |
| VALID | 0x02 | 0x03 | 載具有效訊號 |
| CS_0 | 0x04 | 0x05 | Carrier Slot 0 選擇 |
| TR_REQ | 0x0A | 0x0B | Transfer Request |
| BUSY | 0x0C | 0x0D | 設備忙碌中 |
| COMPT | 0x0E | 0x0F | 傳輸完成 |
| CONT | 0x10 | 0x11 | Continue 訊號 |
| L_REQ | 0x12 | 0x13 | Load Request |
| U_REQ | 0x14 | 0x15 | Unload Request |
| READY | 0x18 | 0x19 | 設備準備好 |
| HOAVBL | 0x1E | 0x1F | Handoff Available |
| ES | 0x20 | 0x21 | Equipment Status |

### E84 狀態事件（71 系列）

| 代碼 | 說明 |
|------|------|
| 0x01 | 設備 Auto Online |
| 0x02 | 可伸出手臂放貨 |
| 0x03 | 設備已接收貨（手臂回收的時機） |
| 0x1002 | 可伸出手臂取貨 |
| 0x1003 | 設備已取貨（手臂回收的時機） |

### E84 警報事件（0x0080 系列）

E84 設備會在發生異常狀況時主動發送警報事件通知 AGV。

#### 警報訊息格式

```
AA 55 00 80 [PARAM_H] [PARAM_L] [STATUS] [CHECKSUM]
```

#### 警報類型

| 參數 H | 參數 L | 說明 | 完整訊息範例 |
|--------|--------|------|--------------|
| 0x00 | 0x00 | E84 Off-line（設備離線） | `AA 55 00 80 00 00 00 ??` |
| 0x40 | 0x00 | TA1 timeout | `AA 55 00 80 40 00 00 CF` |
| 0x40 | 0x01 | TA2 timeout | `AA 55 00 80 40 01 00 CF` |
| 0x40 | 0x02 | TA3 timeout | `AA 55 00 80 40 02 00 CF` |
| 0x40 | 0x03 | TA4 timeout | `AA 55 00 80 40 03 00 CF` |
| 0x40 | 0x04 | Link timeout（連線超時） | `AA 55 00 80 40 04 00 CF` |
| 0x50 | 0x00 | TP3 timeout | `AA 55 00 80 50 00 00 CF` |

#### 警報處理

當收到警報事件時，建議的處理步驟：

1. **記錄警報資訊**：記錄警報類型、時間戳記
2. **停止當前操作**：立即中止正在進行的 Load/Unload 流程
3. **通知操作員**：透過 UI 或日誌系統通知相關人員
4. **執行 Alarm Reset**：在問題解決後執行 `alarm_reset()`
5. **重新初始化**：必要時重新初始化連線和參數

```python
def on_alarm_event(alarm_code: int, description: str):
    """警報事件處理器"""
    logger.error(f"⚠️ E84 警報: {description} (0x{alarm_code:04X})")
    
    # 根據警報類型採取對應措施
    if alarm_code == 0x0000:
        # E84 離線
        logger.critical("設備離線，檢查連線狀態")
    elif (alarm_code & 0xFF00) == 0x4000:
        # Timeout 警報
        timeout_id = alarm_code & 0x00FF
        if timeout_id <= 0x04:
            logger.warning(f"TA{timeout_id+1} 超時，檢查 Timeout 參數設定")
        elif timeout_id == 0x04:
            logger.warning("連線超時，檢查網路連線")
    elif alarm_code == 0x5000:
        # TP3 timeout
        logger.warning("TP3 超時")
    
    # 建議操作
    logger.info("建議執行: 1) 檢查設備狀態 2) 執行 alarm_reset() 3) 重新嘗試操作")

# 使用範例
async with E84Client("COM3") as e84:
    # 註冊警報處理器（需要在實作中新增支援）
    # e84.on_alarm_event = on_alarm_event
    
    try:
        await e84.load_async()
    except Exception as e:
        logger.error(f"操作失敗: {e}")
        await e84.alarm_reset()
```

---

## ⚙️ Timeout 參數（TA1-TA16）

E84 協議定義了 16 個 Timeout 參數，用於控制各種操作的超時時間。

### 參數列表

| 參數 | 代碼 | 預設值 | 實際時間 | 說明 |
|------|------|--------|----------|------|
| TA1 | 0x8040 | 0x02 | 0.2 秒 | 訊號回應超時 |
| TA2 | 0x8041 | 0x1E | 3.0 秒 | VALID 超時 |
| TA3 | 0x8042 | 0x3C | 6.0 秒 | TR_REQ 超時 |
| TA4 | 0x8043 | 0x3C | 6.0 秒 | BUSY 超時 |
| TA5 | 0x8044 | 0x02 | 0.2 秒 | COMPT 超時 |
| TA6 | 0x8045 | 0x02 | 0.2 秒 | CONT 超時 |
| TA7 | 0x804E | 0x02 | 0.2 秒 | CS 選擇超時 |
| TA8 | 0x804F | 0x02 | 0.2 秒 | 保留 |
| TA9 | 0x8050 | 0x02 | 0.2 秒 | 保留 |
| TA10 | 0x8051 | 0x02 | 0.2 秒 | 保留 |
| TA11 | 0x8052 | 0x28 | 4.0 秒 | L_REQ/U_REQ 超時 |
| TA12 | 0x8053 | 0x02 | 0.2 秒 | 保留 |
| TA13 | 0x8054 | 0x28 | 4.0 秒 | READY 超時 |
| TA14 | 0x8055 | 0x20 | 3.2 秒 | 手臂操作超時 |
| TA15 | 0x8056 | 0x28 | 4.0 秒 | 完成確認超時 |
| TA16 | 0x8057 | 0x20 | 3.2 秒 | 保留 |

**單位說明**：參數值單位為 0.1 秒，例如 0x02 = 0.2 秒，0x1E = 3.0 秒

### 自定義參數

```python
custom_ta = {
    'TA1': 0x05,   # 0.5 秒
    'TA2': 0x32,   # 5.0 秒
    'TA3': 0x64,   # 10.0 秒
    # ... 其他參數
}

e84 = E84Client("COM3", default_ta_params=custom_ta)
await e84.initialize_timeout_params()
```

---

## 🔍 使用範例

### 範例 1: 簡單 Load 操作

```python
import asyncio
from e84 import E84Client

async def simple_load():
    async with E84Client("COM3", baudrate=9600) as e84:
        # 初始化
        await e84.initialize_timeout_params()
        
        # 執行 Load
        success = await e84.load_async()
        
        if success:
            print("✅ Load 成功")
        else:
            print("❌ Load 失敗")

asyncio.run(simple_load())
```

### 範例 2: 帶事件監控的 Load

```python
import asyncio
from e84 import E84Client

async def monitored_load():
    # 定義事件處理
    def on_sensor(signal: str, state: bool):
        print(f"[訊號] {signal}: {'ON' if state else 'OFF'}")
    
    def on_state(code: int, desc: str):
        print(f"[狀態] {desc}")
    
    # 創建客戶端
    e84 = E84Client(
        "COM3",
        baudrate=9600,
        on_sensor_event=on_sensor,
        on_state_event=on_state
    )
    
    await e84.connect_async()
    
    try:
        await e84.initialize_timeout_params()
        success = await e84.load_async()
        print(f"結果: {'成功' if success else '失敗'}")
    finally:
        await e84.disconnect_async()

asyncio.run(monitored_load())
```

### 範例 3: 生產環境連續操作

```python
import asyncio
from e84 import E84Client

async def production_workflow():
    e84 = E84Client(
        "COM3",
        baudrate=9600,
        auto_reconnect=True,
        reconnect_interval=2.0
    )
    
    await e84.connect_async()
    await e84.initialize_timeout_params()
    
    try:
        # 連續執行多次 Load/Unload
        for i in range(10):
            print(f"\n--- 第 {i+1} 次操作 ---")
            
            # Load
            if await e84.load_async():
                print("✅ Load 成功")
                await asyncio.sleep(2.0)
                
                # Unload
                if await e84.unload_async():
                    print("✅ Unload 成功")
                else:
                    print("❌ Unload 失敗")
                    await e84.alarm_reset()
            else:
                print("❌ Load 失敗")
                await e84.alarm_reset()
            
            await asyncio.sleep(1.0)
    
    finally:
        await e84.disconnect_async()

asyncio.run(production_workflow())
```

### 範例 4: 手動控制步驟

```python
import asyncio
from e84 import E84Client

async def manual_control():
    async with E84Client("COM3", baudrate=9600) as e84:
        # 手動執行每個步驟
        print("Step 1: DB25 Port Open")
        await e84.db25_port_control(open=True)
        
        print("Step 2: SELECT ON")
        await e84.select_control(select_on=True)
        
        print("Step 3: SELECT OFF")
        await e84.select_control(select_on=False)
        
        print("Step 4: Send LOAD")
        await e84.send_load_command()
        
        # 等待特定訊號
        print("等待 L_REQ OFF...")
        # 可以使用 event queue 或檢查訊號狀態
        await asyncio.sleep(5.0)
        
        print("Step 5: ARM Back Complete")
        await e84.arm_back_complete()
        
        print("Step 6: Alarm Reset")
        await e84.alarm_reset()

asyncio.run(manual_control())
```

---

## 🐛 錯誤處理

### 常見錯誤與解決方案

#### 1. 連線失敗

```python
e84 = E84Client("COM3", baudrate=9600)
if not await e84.connect_async():
    print("連線失敗，請檢查：")
    print("1. 串口名稱是否正確")
    print("2. 串口是否被占用")
    print("3. 波特率是否匹配")
    print("4. 串口權限（Linux）")
```

#### 2. 命令超時

```python
try:
    success = await e84.load_async(timeout_per_step=15.0)
except asyncio.TimeoutError:
    print("操作超時")
    await e84.alarm_reset()
```

#### 3. Checksum 錯誤

Checksum 錯誤會被記錄但不會阻止執行：

```python
# 查看日誌
logging.getLogger("e84").setLevel(logging.DEBUG)
```

#### 4. 訊號等待超時

```python
# 增加超時時間
success = await e84.load_async(timeout_per_step=30.0)

# 或檢查設備狀態
if not success:
    print("檢查設備是否在正確狀態")
    await e84.alarm_reset()
```

---

## 📈 最佳實踐

### 1. 初始化順序

```python
async with E84Client("COM3") as e84:
    # 1. 讀取版本確認通訊正常
    version = await e84.read_firmware_version()
    
    # 2. 初始化 TA 參數
    await e84.initialize_timeout_params()
    
    # 3. 執行業務邏輯
    await e84.load_async()
```

### 2. 錯誤恢復

```python
max_retries = 3
for attempt in range(max_retries):
    success = await e84.load_async()
    if success:
        break
    
    print(f"第 {attempt+1} 次嘗試失敗")
    await e84.alarm_reset()
    await asyncio.sleep(2.0)
```

### 3. 日誌記錄

```python
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e84.log'),
        logging.StreamHandler()
    ]
)

# E84 專用 logger
e84_logger = logging.getLogger("e84")
e84_logger.setLevel(logging.DEBUG)
```

### 4. 資源管理

```python
# ✅ 推薦：使用 Context Manager
async with E84Client("COM3") as e84:
    await e84.load_async()
# 自動斷線

# ❌ 不推薦：手動管理
e84 = E84Client("COM3")
await e84.connect_async()
try:
    await e84.load_async()
finally:
    await e84.disconnect_async()  # 容易忘記
```

---

## 📚 API 參考

### E84Client 類別

#### 初始化方法

- `__init__(port, baudrate=9600, **kwargs)` - 創建實例
- `connect_async()` - 非同步連線
- `disconnect_async()` - 非同步斷線
- `connect()` - 同步連線
- `disconnect()` - 同步斷線

#### 基本命令

- `read_firmware_version()` - 讀取韌體版本
- `set_timeout_param(ta_number, value)` - 設定 TA 參數
- `initialize_timeout_params()` - 初始化所有 TA 參數
- `db25_port_control(open)` - DB25 Port 控制
- `select_control(select_on)` - SELECT 控制
- `send_load_command()` - 發送 LOAD 命令
- `send_unload_command()` - 發送 UNLOAD 命令
- `arm_back_complete(is_unload)` - 手臂回收完成
- `alarm_reset()` - Alarm Reset

#### 高階操作

- `load_async(timeout_per_step)` - 完整 Load 流程
- `unload_async(timeout_per_step)` - 完整 Unload 流程
- `get_event(timeout)` - 從佇列獲取事件
- `get_signal_state(signal_name)` - 查詢訊號狀態

---

## 🧪 測試

運行範例程式：

```bash
python e84_example.py
```

查看所有範例：
1. 基本使用
2. Context Manager
3. Callbacks 事件處理
4. Event Queue 事件處理
5. 混合模式
6. 完整 Load 流程
7. 完整 Unload 流程
8. 錯誤處理
9. 手動控制步驟
10. 生產環境模式

---

## 📖 相關文件

- `QUICK_REF_E84.md` - 快速參考指南
- `e84_example.py` - 使用範例
- `e84_active_protocol.txt` - 協議記錄
- `README_SERIAL.md` - AsyncSerialPort 文檔 (serial_gyro.py)

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

## 📄 授權

MIT License

---

**作者**: SmartIO-AGV Team  
**更新時間**: 2025-11-02  
**版本**: 1.0.0
