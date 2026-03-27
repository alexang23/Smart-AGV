# E84 Protocol Quick Reference

## 📋 快速入門

### 基本使用
```python
from e84 import E84Client

# 創建客戶端
async with E84Client("COM3", baudrate=9600) as e84:
    # 自動 Load
    success = await e84.load_async()
```

---

## 🔧 初始化參數

| 參數 | 說明 | 預設值 | 範例 |
|------|------|--------|------|
| `port` | 串口名稱 | 必填 | `"COM3"` (Win), `"/dev/ttyUSB0"` (Linux) |
| `baudrate` | 波特率 | 9600 | 9600, 115200 |
| `on_sensor_event` | 感測器事件回調 | None | `lambda s, v: print(s, v)` |
| `on_state_event` | 狀態事件回調 | None | `lambda c, d: print(d)` |
| `event_queue_size` | 事件佇列大小 | None | 50, 100, 200 |

---

## 📨 常用命令

### 基本命令

| 方法 | 說明 | 回傳值 |
|------|------|--------|
| `read_firmware_version()` | 讀取韌體版本 | `(major, minor)` |
| `initialize_timeout_params()` | 初始化 TA1-TA16 | `bool` |
| `db25_port_control(open)` | DB25 Port 控制 | `bool` |
| `select_control(select_on)` | SELECT 控制 | `bool` |
| `send_load_command()` | 發送 LOAD 命令 | `bool` |
| `send_unload_command()` | 發送 UNLOAD 命令 | `bool` |
| `arm_back_complete()` | 手臂回收完成 | `bool` |
| `alarm_reset()` | Alarm Reset | `bool` |

### 高階命令

| 方法 | 說明 | 參數 | 回傳值 |
|------|------|------|--------|
| `load_async(timeout_per_step)` | 完整 Load 流程 | 每步超時(秒) | `bool` |
| `unload_async(timeout_per_step)` | 完整 Unload 流程 | 每步超時(秒) | `bool` |
| `get_event(timeout)` | 獲取事件（佇列） | 超時時間 | `E84Event` |
| `get_signal_state(signal_name)` | 查詢訊號狀態 | 訊號名稱 | `bool` or `None` |

---

## 🔢 命令代碼對照表

### 讀取命令 (00 系列)

| 命令 | 代碼 | 說明 |
|------|------|------|
| `READ_FIRMWARE` | 0x0000 | 讀取韌體版本 |
| `READ_CONFIG` | 0x0020 | 讀取配置 |

### 寫入命令 (80 系列)

| 命令 | 代碼 | 說明 | 參數 |
|------|------|------|------|
| `DB25_PORT` | 0x8001 | DB25 Port 控制 | 0x0001=Open, 0x0000=Close |
| `ALARM_RESET` | 0x8002 | Alarm Reset | 0x0000 |
| `LOAD_UNLOAD` | 0x8003 | Load/Unload | 0x0000=Load, 0x0001=Unload |
| `ARM_BACK` | 0x8004 | 手臂回收完成 | 0x0001 |
| `CS_SELECT` | 0x8006 | CS 選擇 | 0x0000=CS0 |
| `CONTINUE` | 0x8008 | Continue Signal | 0x0000 |
| `SELECT_CONTROL` | 0x8012 | SELECT 控制 | 0x0004=ON, 0x0000=OFF |

### Timeout 參數 (TA1-TA16)

| 參數 | 代碼 | 預設值 | 說明 |
|------|------|--------|------|
| TA1 | 0x8040 | 0x02 | 0.2 秒 |
| TA2 | 0x8041 | 0x1E | 3.0 秒 |
| TA3 | 0x8042 | 0x3C | 6.0 秒 |
| TA4 | 0x8043 | 0x3C | 6.0 秒 |
| TA5 | 0x8044 | 0x02 | 0.2 秒 |
| TA6 | 0x8045 | 0x02 | 0.2 秒 |
| TA7 | 0x804E | 0x02 | 0.2 秒 |
| TA8 | 0x804F | 0x02 | 0.2 秒 |
| TA9 | 0x8050 | 0x02 | 0.2 秒 |
| TA10 | 0x8051 | 0x02 | 0.2 秒 |
| TA11 | 0x8052 | 0x28 | 4.0 秒 |
| TA12 | 0x8053 | 0x02 | 0.2 秒 |
| TA13 | 0x8054 | 0x28 | 4.0 秒 |
| TA14 | 0x8055 | 0x20 | 3.2 秒 |
| TA15 | 0x8056 | 0x28 | 4.0 秒 |
| TA16 | 0x8057 | 0x20 | 3.2 秒 |

**注意**: 參數值單位為 0.1 秒，例如 0x02 = 0.2 秒

---

## 🚦 訊號定義 (70 系列事件)

| 訊號名稱 | 代碼 (ON/OFF) | 說明 |
|----------|---------------|------|
| GO | 0x00 / 0x01 | GO 訊號 |
| VALID | 0x02 / 0x03 | VALID 訊號 |
| CS_0 | 0x04 / 0x05 | Carrier Slot 0 |
| TR_REQ | 0x0A / 0x0B | Transfer Request |
| BUSY | 0x0C / 0x0D | BUSY 訊號 |
| COMPT | 0x0E / 0x0F | Complete 訊號 |
| CONT | 0x10 / 0x11 | Continue 訊號 |
| L_REQ | 0x12 / 0x13 | Load Request |
| U_REQ | 0x14 / 0x15 | Unload Request |
| READY | 0x18 / 0x19 | READY 訊號 |
| HOAVBL | 0x1E / 0x1F | Handoff Available |
| ES | 0x20 / 0x21 | Equipment Status |

**規則**: 偶數=ON, 奇數=OFF

---

## 🔄 狀態事件 (71 系列)

| 代碼 | 說明 |
|------|------|
| 0x01 | 設備 Auto Online |
| 0x02 | 可伸出手臂放貨 |
| 0x03 | 設備已接收貨（手臂回收時機） |
| 0x1002 | 可伸出手臂取貨 |
| 0x1003 | 設備已取貨（手臂回收時機） |

---

## ⚠️ 警報事件 (0x0080 系列)

E84 設備會在異常狀況時主動發送警報通知。

### 警報類型

| 警報名稱 | 參數 H | 參數 L | 完整訊息範例 |
|----------|--------|--------|--------------|
| E84 Off-line | 0x00 | 0x00 | `AA 55 00 80 00 00 00 ??` |
| TA1 timeout | 0x40 | 0x00 | `AA 55 00 80 40 00 00 CF` |
| TA2 timeout | 0x40 | 0x01 | `AA 55 00 80 40 01 00 CF` |
| TA3 timeout | 0x40 | 0x02 | `AA 55 00 80 40 02 00 CF` |
| TA4 timeout | 0x40 | 0x03 | `AA 55 00 80 40 03 00 CF` |
| Link timeout | 0x40 | 0x04 | `AA 55 00 80 40 04 00 CF` |
| TP3 timeout | 0x50 | 0x00 | `AA 55 00 80 50 00 00 CF` |

### 警報處理流程

```
收到警報 (0x0080)
   ↓
記錄警報資訊
   ↓
停止當前操作
   ↓
檢查設備狀態
   ↓
執行 alarm_reset()
   ↓
重新嘗試操作
```

---

## 📊 Load 流程步驟

```
1. DB25 Port Open (0x8001, 0x0001)
   ↓
2. SELECT ON (0x8012, 0x0004)
   ↓
3. SELECT OFF (0x8012, 0x0000)
   ↓
4. LOAD Command (0x8003, 0x0000)
   ↓
5. 等待訊號序列:
   - CS_0 ON
   - VALID ON
   - L_REQ ON
   - TR_REQ ON
   - READY ON
   - BUSY ON
   ↓
6. 等待 L_REQ OFF (可伸出手臂放貨)
   ↓
7. ARM Back Complete (0x8004, 0x0001)
   ↓
8. 等待完成訊號:
   - BUSY OFF
   - TR_REQ OFF
   - COMPT ON
   - READY OFF
   - VALID OFF
   - COMPT OFF
   - CS_0 OFF
   ↓
9. Alarm Reset (0x8002, 0x0000)
```

---

## 📊 Unload 流程步驟

```
1. DB25 Port Open (0x8001, 0x0001)
   ↓
2. SELECT ON (0x8012, 0x0004)
   ↓
3. SELECT OFF (0x8012, 0x0000)
   ↓
4. UNLOAD Command (0x8003, 0x0001)
   ↓
5. 等待訊號序列:
   - CS_0 ON
   - VALID ON
   - U_REQ ON  ← 注意是 U_REQ 不是 L_REQ
   - TR_REQ ON
   - READY ON
   - BUSY ON
   ↓
6. 等待 U_REQ OFF (可伸出手臂取貨)
   ↓
7. ARM Back Complete (0x8004, 0x0001)
   ↓
8. 等待完成訊號:
   - BUSY OFF
   - TR_REQ OFF
   - COMPT ON
   - READY OFF
   - VALID OFF
   - COMPT OFF
   - CS_0 OFF
   ↓
9. Alarm Reset (0x8002, 0x0000)
```

---

## 💡 使用技巧

### 1. 事件處理模式選擇

| 場景 | 推薦模式 | 原因 |
|------|---------|------|
| 簡單監控 | Callbacks | 即時、簡單 |
| 複雜流程 | Event Queue | 順序保證、不阻塞 |
| 生產環境 | Hybrid | 兼具即時性和靈活性 |

### 2. 超時設定建議

| 環境 | timeout_per_step | 原因 |
|------|------------------|------|
| 測試環境 | 30.0 秒 | 允許手動干預 |
| 生產環境 | 15.0 秒 | 快速失敗，避免堵塞 |
| 不穩定網路 | 20.0 秒 | 容忍延遲 |

### 3. 錯誤處理建議

```python
# ✅ 好的做法
try:
    success = await e84.load_async()
    if not success:
        await e84.alarm_reset()
        # 重試一次
        success = await e84.load_async()
except Exception as e:
    logger.error(f"Load 失敗: {e}")
    await e84.alarm_reset()
```

```python
# ❌ 不好的做法
success = await e84.load_async()
# 沒有檢查結果，直接繼續
```

### 4. 日誌級別設定

```python
# 開發環境：查看所有細節
logging.basicConfig(level=logging.DEBUG)

# 生產環境：只記錄重要信息
logging.basicConfig(level=logging.INFO)

# 僅錯誤：最小化日誌
logging.basicConfig(level=logging.ERROR)
```

---

## ⚠️ 常見問題

### Q1: 連線失敗怎麼辦？
**A**: 檢查：
1. 串口名稱是否正確 (`COM3`, `/dev/ttyUSB0`)
2. 串口是否被其他程序占用
3. 波特率是否匹配（預設 9600）
4. 串口權限（Linux 需要 `sudo` 或加入 `dialout` 群組）

### Q2: Load/Unload 超時怎麼辦？
**A**: 
1. 增加 `timeout_per_step` 參數
2. 檢查設備是否處於正確狀態
3. 查看日誌確定卡在哪個步驟
4. 嘗試 `alarm_reset()`

### Q3: 如何調試事件處理？
**A**:
```python
# 啟用 DEBUG 日誌
logging.getLogger("e84").setLevel(logging.DEBUG)

# 使用 Callbacks 即時查看
def debug_callback(signal, state):
    print(f"DEBUG: {signal} = {state}")

e84 = E84Client("COM3", on_sensor_event=debug_callback)
```

### Q4: Checksum 錯誤怎麼辦？
**A**: 
- 檢查訊息是否完整接收
- 可能是設備 checksum 算法不同
- 程式碼會記錄警告但繼續執行

### Q5: 如何自定義 TA 參數？
**A**:
```python
custom_ta = {
    'TA1': 0x05,  # 0.5 秒
    'TA2': 0x32,  # 5.0 秒
    # ... 其他
}

e84 = E84Client("COM3", default_ta_params=custom_ta)
```

---

## 📚 相關文件

- `README_E84.md` - 完整文檔
- `e84_example.py` - 使用範例
- `e84_active_protocol.txt` - 協議記錄
- `serial_gyro.py` - 底層串口通訊

---

## 🔗 相關連結

- E84 Protocol 標準: [SEMI E84](https://www.semi.org/)
- AsyncSerialPort 文檔: `README_SERIAL.md`
- 問題回報: GitHub Issues

---

**更新時間**: 2025-11-02  
**版本**: 1.0.0
