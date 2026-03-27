"""
Active E84 Protocol Implementation - AGV 與設備通訊協議 (Synchronous Version)

主要功能：
1. E84 訊息解析與建構
2. Checksum 計算與驗證
3. 命令與回應配對
4. 事件處理 (70/71 系列)
5. 完整的 Load/Unload 流程
6. Timeout 參數管理 (TA1-TA16)

使用範例：
    # 基本使用
    with ActiveE84("COM3", baudrate=9600) as e84:
        # 自動 Load 流程
        success = e84.load()
        if success:
            print("Load 完成")
    
    # 帶事件監控
    def on_sensor(signal: str, state: bool):
        print(f"感測器 {signal}: {state}")
    
    e84 = ActiveE84("COM3", on_sensor_event=on_sensor, event_queue_size=50)
    e84.connect()
    success = e84.load()
"""

import time
import logging
import queue
from typing import Optional, Callable, Tuple, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from sync_serial_gyro import SyncSerialPort, ProtocolMode
from sync_rf_sensor import SyncRFSensor, CommunicationMedium

# 設定 logger
logger = logging.getLogger(__name__)


# ==================== E84 訊息格式定義 ====================

class E84MessageType(Enum):
    """E84 訊息類型"""
    WRITE = "write"  # 55 AA 開頭
    READ = "read"    # AA 55 開頭


class E84CommandSeries(Enum):
    """E84 命令系列"""
    READ = 0x00      # 00 系列：讀取
    WRITE = 0x80     # 80 系列：寫入
    SENSOR_EVENT = 0x70  # 70 系列：感測器事件
    STATE_EVENT = 0x71   # 71 系列：狀態事件
    ALARM_EVENT = 0x80   # 80 系列：警報事件 (0x0080)


@dataclass
class E84Message:
    """
    E84 訊息資料結構
    
    WRITE 格式: 55 AA [CMD_H] [CMD_L] [PARAM_H] [PARAM_L] [CHECKSUM]
    READ 格式:  AA 55 [CMD_H] [CMD_L] [DATA_H] [DATA_L] [STATUS] [CHECKSUM]
    """
    msg_type: E84MessageType
    command: int  # 2 bytes command (0x0000 - 0xFFFF)
    data: int     # 2 bytes data/param (0x0000 - 0xFFFF)
    status: int = 0x00  # 僅 READ 訊息有效
    checksum: int = 0x00
    raw_bytes: bytes = b''
    
    @property
    def command_high(self) -> int:
        """命令高位元組"""
        return (self.command >> 8) & 0xFF
    
    @property
    def command_low(self) -> int:
        """命令低位元組"""
        return self.command & 0xFF
    
    @property
    def data_high(self) -> int:
        """資料高位元組"""
        return (self.data >> 8) & 0xFF
    
    @property
    def data_low(self) -> int:
        """資料低位元組"""
        return self.data & 0xFF
    
    @property
    def series(self) -> int:
        """命令系列（高位元組）"""
        return self.command_high
    
    def __str__(self) -> str:
        """字串表示"""
        if self.msg_type == E84MessageType.WRITE:
            return f"WRITE: 55 AA {self.command_high:02X} {self.command_low:02X} {self.data_high:02X} {self.data_low:02X} {self.checksum:02X}"
        else:
            return f"READ:  AA 55 {self.command_high:02X} {self.command_low:02X} {self.data_high:02X} {self.data_low:02X} {self.status:02X} {self.checksum:02X}"


@dataclass
class E84Event:
    """
    E84 事件資料結構（70/71/80 系列）
    """
    series: int  # 0x70 或 0x71 或 0x80
    code: int    # 事件代碼
    timestamp: float
    message: E84Message
    signal_name: str = ""
    description: str = ""
    alarm_type: str = ""  # 警報類型（僅 0x80 系列）


# ==================== E84 訊號定義 ====================

class E84Signal:
    """E84 訊號名稱定義（70 系列）"""
    # 基本訊號
    GO = 0x00
    VALID = 0x02
    CS_0 = 0x04
    TR_REQ = 0x0A
    BUSY = 0x0C
    COMPT = 0x0E
    CONT = 0x10
    L_REQ = 0x12
    U_REQ = 0x14
    READY = 0x18
    HOAVBL = 0x1E
    ES = 0x20
    
    # 訊號名稱對照表
    SIGNAL_NAMES = {
        0x00: "GO",
        0x01: "GO",
        0x02: "VALID",
        0x03: "VALID",
        0x04: "CS_0",
        0x05: "CS_0",
        0x0A: "TR_REQ",
        0x0B: "TR_REQ",
        0x0C: "BUSY",
        0x0D: "BUSY",
        0x0E: "COMPT",
        0x0F: "COMPT",
        0x10: "CONT",
        0x11: "CONT",
        0x12: "L_REQ",
        0x13: "L_REQ",
        0x14: "U_REQ",
        0x15: "U_REQ",
        0x18: "READY",
        0x19: "READY",
        0x1E: "HOAVBL",
        0x1F: "HOAVBL",
        0x20: "ES",
        0x21: "ES",
    }
    
    @staticmethod
    def get_signal_name(code: int) -> str:
        """取得訊號名稱"""
        return E84Signal.SIGNAL_NAMES.get(code, f"UNKNOWN_0x{code:02X}")
    
    @staticmethod
    def is_signal_on(code: int) -> bool:
        """判斷訊號是 ON 還是 OFF（偶數=ON, 奇數=OFF）"""
        return (code % 2) == 0


class E84StateEvent:
    """E84 狀態事件定義（71 系列）"""
    AUTO_ONLINE = 0x01
    READY_TO_LOAD = 0x02      # 可伸出手臂放貨
    LOAD_RECEIVED = 0x03      # 設備已接收貨
    READY_TO_UNLOAD = 0x1002  # 可伸出手臂取貨
    UNLOAD_COMPLETE = 0x1003  # 設備已取貨
    
    STATE_DESCRIPTIONS = {
        0x01: "設備 Auto Online",
        0x02: "可伸出手臂放貨",
        0x03: "設備已接收貨（手臂回收的時機）",
        0x1002: "可伸出手臂取貨",
        0x1003: "設備已取貨（手臂回收的時機）",
    }
    
    @staticmethod
    def get_description(code: int) -> str:
        """取得狀態描述"""
        return E84StateEvent.STATE_DESCRIPTIONS.get(code, f"未知狀態 0x{code:04X}")


class E84AlarmEvent:
    """E84 警報事件定義（0x0080 系列）"""
    
    # 警報類型
    OFFLINE = "offline"           # E84 離線
    TA_TIMEOUT = "ta_timeout"     # TA1-TA4 超時
    LINK_TIMEOUT = "link_timeout" # 連線超時
    TP3_TIMEOUT = "tp3_timeout"   # TP3 超時
    UNKNOWN = "unknown"           # 未知警報
    
    # 警報代碼
    ALARM_OFFLINE = 0x0000        # E84 Off-line
    ALARM_TA1 = 0x4000            # TA1 timeout
    ALARM_TA2 = 0x4001            # TA2 timeout
    ALARM_TA3 = 0x4002            # TA3 timeout
    ALARM_TA4 = 0x4003            # TA4 timeout
    ALARM_LINK = 0x4004           # Link timeout
    ALARM_TP3 = 0x5000            # TP3 timeout
    
    # 警報描述對照表
    ALARM_DESCRIPTIONS = {
        0x0000: "E84 Off-line（設備離線）",
        0x4000: "TA1 timeout",
        0x4001: "TA2 timeout",
        0x4002: "TA3 timeout",
        0x4003: "TA4 timeout",
        0x4004: "Link timeout（連線超時）",
        0x5000: "TP3 timeout",
    }
    
    @staticmethod
    def get_alarm_type(code: int) -> str:
        """
        根據警報代碼取得警報類型
        
        Args:
            code: 警報代碼
        
        Returns:
            警報類型字串
        """
        if code == 0x0000:
            return E84AlarmEvent.OFFLINE
        elif 0x4000 <= code <= 0x4003:
            return E84AlarmEvent.TA_TIMEOUT
        elif code == 0x4004:
            return E84AlarmEvent.LINK_TIMEOUT
        elif code == 0x5000:
            return E84AlarmEvent.TP3_TIMEOUT
        else:
            return E84AlarmEvent.UNKNOWN
    
    @staticmethod
    def get_description(code: int) -> str:
        """
        取得警報描述
        
        Args:
            code: 警報代碼
        
        Returns:
            警報描述字串
        """
        return E84AlarmEvent.ALARM_DESCRIPTIONS.get(code, f"未知警報 0x{code:04X}")


# ==================== E84 命令定義 ====================

class E84Command:
    """E84 命令定義"""
    # 讀取命令 (00 系列)
    READ_FIRMWARE = 0x0000
    READ_CONFIG = 0x0020
    
    # 寫入命令 (80 系列)
    DB25_PORT = 0x8001        # DB25 Port 控制
    ALARM_RESET = 0x8002      # Alarm Reset
    LOAD_UNLOAD = 0x8003      # Load/Unload
    ARM_BACK = 0x8004         # 手臂回收完成
    CS_SELECT = 0x8006        # CS 選擇
    CONTINUE = 0x8008         # Continue Signal
    SELECT_CONTROL = 0x8012   # SELECT 控制
    SENSOR_EVENT = 0x8013     # 事件解碼控制
    ALARM_MODE = 0x8022       # Alarm 模式
    
    # Timeout 參數 (TA1-TA16)
    TA1 = 0x8040
    TA2 = 0x8041
    TA3 = 0x8042
    TA4 = 0x8043
    TA5 = 0x8044
    TA6 = 0x8045
    TA7 = 0x804E
    TA8 = 0x804F
    TA9 = 0x8050
    TA10 = 0x8051
    TA11 = 0x8052
    TA12 = 0x8053
    TA13 = 0x8054
    TA14 = 0x8055
    TA15 = 0x8056
    TA16 = 0x8057
    
    UNKNOWN_0x8067 = 0x8067
    INPUT_TIMEOUT = 0x804D    # DB25 INPUT 延遲 TIMEOUT


# ==================== E84 協議處理 ====================

class E84Protocol:
    """E84 協議解析與建構"""
    
    # 訊息頭定義
    HEADER_WRITE = bytes([0x55, 0xAA])
    HEADER_READ = bytes([0xAA, 0x55])
    
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """
        計算 checksum (簡單累加 modulo 256)
        
        Args:
            data: 要計算的資料（不含 checksum）
        
        Returns:
            checksum 值 (0x00-0xFF)
        """
        return sum(data) & 0xFF
    
    @staticmethod
    def build_write_message(command: int, param: int) -> bytes:
        """
        建構 WRITE 訊息
        
        Args:
            command: 命令代碼 (2 bytes)
            param: 參數值 (2 bytes)
        
        Returns:
            完整的訊息 bytes
        """
        cmd_h = (command >> 8) & 0xFF
        cmd_l = command & 0xFF
        param_h = (param >> 8) & 0xFF
        param_l = param & 0xFF
        
        # 組合訊息（不含 checksum）
        message = E84Protocol.HEADER_WRITE + bytes([cmd_h, cmd_l, param_h, param_l])
        
        # 計算並附加 checksum
        checksum = E84Protocol.calculate_checksum(message)
        message += bytes([checksum])
        
        return message
    
    @staticmethod
    def parse_message(data: bytes) -> Optional[E84Message]:
        """
        解析接收到的訊息
        
        Args:
            data: 原始訊息 bytes
        
        Returns:
            E84Message 物件，解析失敗返回 None
        """
        if len(data) < 7:
            logger.warning(f"訊息長度不足: {len(data)} bytes")
            return None
        
        # 判斷訊息類型
        if data[0:2] == E84Protocol.HEADER_WRITE:
            # WRITE 訊息: 55 AA [CMD_H] [CMD_L] [PARAM_H] [PARAM_L] [CHECKSUM]
            if len(data) < 7:
                return None
            
            msg_type = E84MessageType.WRITE
            command = (data[2] << 8) | data[3]
            param = (data[4] << 8) | data[5]
            checksum = data[6]
            status = 0x00
            
        elif data[0:2] == E84Protocol.HEADER_READ:
            # READ 訊息: AA 55 [CMD_H] [CMD_L] [DATA_H] [DATA_L] [STATUS] [CHECKSUM]
            if len(data) < 8:
                return None
            
            msg_type = E84MessageType.READ
            command = (data[2] << 8) | data[3]
            param = (data[4] << 8) | data[5]
            status = data[6]
            checksum = data[7]
            
        else:
            logger.warning(f"未知的訊息頭: {data[0]:02X} {data[1]:02X}")
            return None
        
        # 驗證 checksum
        if msg_type == E84MessageType.WRITE:
            expected_checksum = E84Protocol.calculate_checksum(data[0:6])
        else:
            expected_checksum = E84Protocol.calculate_checksum(data[0:7])
        
        if checksum != expected_checksum:
            logger.warning(f"Checksum 錯誤: 期望 0x{expected_checksum:02X}, 收到 0x{checksum:02X}")
            # 不返回 None，僅警告，因為有些設備可能 checksum 不正確
        
        return E84Message(
            msg_type=msg_type,
            command=command,
            data=param,
            status=status,
            checksum=checksum,
            raw_bytes=data
        )


# ==================== Active E84 Client ====================

class ActiveE84(SyncSerialPort):
    """
    Active E84 協議客戶端 (Synchronous Version)
    
    繼承 SyncSerialPort，提供完整的 E84 通訊功能：
    1. 基本 E84 命令
    2. Timeout 參數設定 (TA1-TA16)
    3. 事件處理 (Callbacks + Queue)
    4. 警報事件處理 (0x0080 系列)
    5. 完整的 Load/Unload 流程
    
    Args:
        port: 串口名稱
        baudrate: 波特率
        rf_port: RF Sensor 串口名稱（預設與主串口相同）
        on_sensor_event: 感測器事件回調 (70 系列)
        on_state_event: 狀態事件回調 (71 系列)
        on_alarm_event: 警報事件回調 (80 系列)
        event_queue_size: 事件佇列大小（None=不使用佇列）
        **kwargs: 其他 SyncSerialPort 參數
    
    使用範例：
        # 基本使用
        with ActiveE84("COM3") as e84:
            success = e84.load()
        
        # 帶事件監控
        def on_sensor(signal: str, state: bool):
            print(f"{signal}: {state}")
        
        e84 = ActiveE84("COM3", on_sensor_event=on_sensor, event_queue_size=50)
        e84.connect()
        
        # 處理事件
        event = e84.get_event()
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        rf_port: Optional[str] = None,
        # 事件處理
        on_sensor_event: Optional[Callable[[str, bool], None]] = None,
        on_state_event: Optional[Callable[[int, str], None]] = None,
        on_alarm_event: Optional[Callable[[str, int, str], None]] = None,
        event_queue_size: Optional[int] = None,
        # Timeout 參數預設值（單位：0.1 秒）
        default_ta_params: Optional[Dict[str, int]] = None,
        **kwargs
    ):
        """初始化 Active E84 客戶端"""
        # 配置 FRAME 模式用於 E84 二進制協議
        kwargs['protocol_mode'] = ProtocolMode.FRAME_FIXED  # 固定長度 FRAME 模式
        kwargs['frame_header'] = b'\xAA\x55'  # E84 READ 訊息頭 (設備→AGV)
        kwargs['frame_length'] = 8  # E84 READ 訊息長度
        kwargs['checksum_enabled'] = True  # 啟用 checksum 驗證
        kwargs['max_buffer_size'] = 256  # 緩衝區大小
        kwargs['response_parser'] = self._e84_response_parser
        
        # 初始化父類別（FRAME 模式）
        super().__init__(port=port, baudrate=baudrate, **kwargs)
        
        # RF Sensor 串口配置
        self._rf_port = rf_port if rf_port else port
        
        # 事件處理
        self._on_sensor_event = on_sensor_event
        self._on_state_event = on_state_event
        self._on_alarm_event = on_alarm_event
        self._event_queue: Optional[queue.Queue] = None
        if event_queue_size:
            self._event_queue = queue.Queue(maxsize=event_queue_size)
        
        # TA 參數預設值
        self._ta_params = default_ta_params or {
            'TA1': 0x02, 'TA2': 0x1E, 'TA3': 0x3C, 'TA4': 0x3C,
            'TA5': 0x02, 'TA6': 0x02, 'TA7': 0x02, 'TA8': 0x02,
            'TA9': 0x02, 'TA10': 0x02, 'TA11': 0x28, 'TA12': 0x02,
            'TA13': 0x28, 'TA14': 0x20, 'TA15': 0x28, 'TA16': 0x20,
        }
        
        # 內部狀態
        self._current_signals: Dict[str, bool] = {}  # 當前訊號狀態
        self._last_message: Optional[E84Message] = None
        
        logger.info(f"ActiveE84 初始化: {port} @ {baudrate}")
    
    def _e84_response_parser(self, data: bytes) -> Tuple[Optional[str], bytes]:
        """
        E84 回應解析器（FRAME 模式）
        
        在 FRAME 模式下，父類別已經：
        1. 尋找並驗證 frame header (0xAA55)
        2. 提取完整的 8 字節幀
        3. 驗證 checksum
        
        此解析器只需要解析已驗證的完整幀
        
        Args:
            data: 完整且已驗證的 E84 READ 幀（8 bytes）
        
        Returns:
            (command_id, remaining_data) - remaining_data 在 FRAME 模式下總是空
        """
        # FRAME 模式：data 已經是完整且驗證過的幀
        if len(data) < 8:
            logger.warning(f"收到不完整的幀: {len(data)} bytes - {data.hex()}")
            return (None, b'')
        
        # 驗證 header（雙重檢查）
        if data[0:2] != E84Protocol.HEADER_READ:
            logger.warning(f"收到非 READ 訊息頭: {data[0:2].hex()}")
            return (None, b'')
        
        # 解析 E84 訊息
        message = E84Protocol.parse_message(data)
        
        if not message:
            logger.warning(f"無法解析 E84 訊息: {data.hex()}")
            return (None, b'')
        
        self._last_message = message
        logger.debug(f"解析 E84 訊息: {message}")
        logger.info(f"DEBUG: _e84_response_parser 解析 E84 訊息: {message}")
        
        # 處理事件訊息 (70/71/80 系列)
        if message.command == 0x70:
            # 感測器事件
            logger.info(f"DEBUG: _e84_response_parser 0x70: {message}")
            self._handle_sensor_event(message)
        elif message.command == 0x71:
            # 狀態事件
            logger.info(f"DEBUG: _e84_response_parser 0x71: {message}")
            self._handle_state_event(message)
        elif message.command == 0x80:
            # 警報事件
            logger.info(f"DEBUG: _e84_response_parser 0x80: {message}")
            self._handle_alarm_event(message)
        
        # 返回 command_id 用於命令匹配
        command_id = f"E84_{message.command:04X}"
        
        # FRAME 模式：沒有剩餘資料（每個幀都是完整的）
        return (command_id, b'')
    
    def _handle_sensor_event(self, message: E84Message) -> None:
        """處理感測器事件 (70 系列)"""
        code = message.data_low
        signal_name = E84Signal.get_signal_name(code)
        state = E84Signal.is_signal_on(code)
        
        # 更新內部狀態
        self._current_signals[signal_name] = state
        
        # 建立事件物件
        event = E84Event(
            series=0x70,
            code=code,
            timestamp=time.time(),
            message=message,
            signal_name=signal_name,
            description=f"{signal_name} {'ON' if state else 'OFF'}"
        )
        
        logger.debug(f"感測器事件: {signal_name} = {state}")
        
        # 1. Callback 立即執行
        if self._on_sensor_event:
            try:
                self._on_sensor_event(signal_name, state)
            except Exception as e:
                logger.error(f"感測器事件回調錯誤: {e}")
        
        # 2. 放入事件佇列
        if self._event_queue:
            try:
                self._event_queue.put(event, block=False)
            except queue.Full:
                logger.warning("事件佇列已滿，丟棄舊事件")
    
    def _handle_state_event(self, message: E84Message) -> None:
        """處理狀態事件 (71 系列)"""
        # 71 系列可能有不同的資料格式
        code = message.data
        description = E84StateEvent.get_description(code)
        
        # 建立事件物件
        event = E84Event(
            series=0x71,
            code=code,
            timestamp=time.time(),
            message=message,
            signal_name="STATE",
            description=description
        )
        
        logger.info(f"狀態事件: {description}")
        
        # 1. Callback 立即執行
        if self._on_state_event:
            try:
                logger.info(f"狀態事件: _on_state_event {description}")
                self._on_state_event(code, description)
            except Exception as e:
                logger.error(f"狀態事件回調錯誤: {e}")
        
        # 2. 放入事件佇列
        if self._event_queue:
            try:
                logger.info(f"狀態事件: _event_queue {description}")
                self._event_queue.put(event, block=False)
            except queue.Full:
                logger.warning("事件佇列已滿，丟棄舊事件")
    
    def _handle_alarm_event(self, message: E84Message) -> None:
        """處理警報事件 (80 系列)"""
        # 解析警報代碼
        alarm_code = message.data
        alarm_type = E84AlarmEvent.get_alarm_type(alarm_code)
        description = E84AlarmEvent.get_description(alarm_code)
        
        # 建立事件物件
        event = E84Event(
            series=0x80,
            code=alarm_code,
            timestamp=time.time(),
            message=message,
            signal_name="ALARM",
            description=description,
            alarm_type=alarm_type
        )
        
        logger.error(f"⚠️ E84 警報事件: {description} (類型: {alarm_type}, 代碼: 0x{alarm_code:04X})")
        
        # 1. Callback 立即執行
        if self._on_alarm_event:
            try:
                self._on_alarm_event(alarm_type, alarm_code, description)
            except Exception as e:
                logger.error(f"警報事件回調錯誤: {e}")
        
        # 2. 放入事件佇列
        if self._event_queue:
            try:
                self._event_queue.put(event, block=False)
            except queue.Full:
                logger.warning("事件佇列已滿，丟棄舊事件")
    
    def get_event(self, timeout: Optional[float] = None) -> E84Event:
        """
        從事件佇列獲取事件（阻塞）
        
        Args:
            timeout: 超時時間（秒），None=永久等待
        
        Returns:
            E84Event 物件
        
        Raises:
            RuntimeError: 事件佇列未啟用
            queue.Empty: 超時
        """
        if not self._event_queue:
            raise RuntimeError("事件佇列未啟用，請在初始化時設定 event_queue_size")
        
        return self._event_queue.get(timeout=timeout)
    
    def get_signal_state(self, signal_name: str) -> Optional[bool]:
        """取得當前訊號狀態"""
        return self._current_signals.get(signal_name)
    
    # ==================== 基本 E84 命令 ====================
    
    def _send_e84_command(
        self, 
        command: int, 
        param: int, 
        timeout: float = 5.0
    ) -> Optional[E84Message]:
        """
        發送 E84 命令並等待回應
        
        Args:
            command: 命令代碼
            param: 參數值
            timeout: 超時時間
        
        Returns:
            回應的 E84Message，失敗返回 None
        """
        # 建構命令
        message = E84Protocol.build_write_message(command, param)
        command_id = f"E84_{command:04X}"
        
        logger.debug(f"發送命令: {command:04X}, 參數: {param:04X}")
        
        try:
            # 發送並等待回應
            response_data = self.send_command(
                command_id=command_id,
                data=message,
                timeout=timeout
            )
            
            # response_data 會是原始 bytes，但已被解析器處理過
            # _last_message 包含最後解析的訊息
            if self._last_message and self._last_message.command == command:
                return self._last_message
            
            return None
            
        except TimeoutError:
            logger.warning(f"命令 0x{command:04X} 超時")
            return None
        except Exception as e:
            logger.error(f"發送命令錯誤: {e}")
            return None
    
    def read_firmware_version(self) -> Optional[Tuple[int, int]]:
        """
        讀取韌體版本
        
        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.READ_FIRMWARE, 0x0000, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"韌體版本: {major}.{minor}")
            return (major, minor)
        return None
    
    def read_config(self) -> Optional[Tuple[int, int]]:
        """
        設定 0020 參數

        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.READ_CONFIG, 0x0000, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"read config: {major}.{minor}")
            return (major, minor)
        return None
    
    def set_unknown_0x8067(self) -> Optional[Tuple[int, int]]:
        """
        設定 0x8067 參數

        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.UNKNOWN_0x8067, 0x0064, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"設定 0x8067 參數: {major}.{minor}")
            return (major, minor)
        return None
    
    def set_sensor_event(self) -> Optional[Tuple[int, int]]:
        """
        設定 sensor event 參數

        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.SENSOR_EVENT, 0x0001, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"設定 sensor event 參數: {major}.{minor}")
            return (major, minor)
        return None

    def set_input_timeout(self) -> Optional[Tuple[int, int]]:
        """
        設定 input timeout 參數

        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.INPUT_TIMEOUT, 0x012c, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"設定 input timeout 參數: {major}.{minor}")
            return (major, minor)
        return None

    def set_alarm_mode(self) -> Optional[Tuple[int, int]]:
        """
        設定 alarm mode 參數

        Returns:
            (major, minor) 版本號，失敗返回 None
        """
        response = self._send_e84_command(E84Command.ALARM_MODE, 0x0000, 5)
        if response:
            major = response.data_high
            minor = response.data_low
            logger.info(f"設定 alarm mode 參數: {major}.{minor}")
            return (major, minor)
        return None
    
    def set_timeout_param(self, ta_number: int, value: int) -> bool:
        """
        設定 Timeout 參數 (TA1-TA16)
        
        Args:
            ta_number: TA 編號 (1-16)
            value: 超時值（單位: 0.1 秒）
        
        Returns:
            是否成功
        """
        if not (1 <= ta_number <= 16):
            logger.error(f"TA 編號錯誤: {ta_number}，必須在 1-16 之間")
            return False
        
        # TA 命令對照
        ta_commands = {
            1: E84Command.TA1, 2: E84Command.TA2, 3: E84Command.TA3, 4: E84Command.TA4,
            5: E84Command.TA5, 6: E84Command.TA6, 7: E84Command.TA7, 8: E84Command.TA8,
            9: E84Command.TA9, 10: E84Command.TA10, 11: E84Command.TA11, 12: E84Command.TA12,
            13: E84Command.TA13, 14: E84Command.TA14, 15: E84Command.TA15, 16: E84Command.TA16,
        }
        
        command = ta_commands[ta_number]
        response = self._send_e84_command(command, value)
        
        if response and response.data == value:
            logger.info(f"設定 TA{ta_number} = 0x{value:04X} ({value * 0.1:.1f} 秒)")
            return True
        return False
    
    def initialize_timeout_params(self) -> bool:
        """
        初始化所有 Timeout 參數
        
        Returns:
            是否全部成功
        """
        logger.info("初始化 TA 參數...")
        success_count = 0
        
        for i in range(1, 17):
            ta_key = f'TA{i}'
            value = self._ta_params.get(ta_key, 0x02)
            if self.set_timeout_param(i, value):
                success_count += 1
            time.sleep(0.05)  # 小延遲避免命令過快
        
        logger.info(f"TA 參數初始化完成: {success_count}/16")
        return success_count == 16
    
    def initialize_device(self, timeout_per_step: float = 5.0) -> bool:
        """
        完整的 initialize_device 流程
        
        流程步驟：
        1. 讀取韌體版本
        2. 讀取配置
        3. 初始化 TA 參數
        4. 設定未知參數 0x8067
        5. 設定感測器事件
        6. 設定輸入超時
        7. 設定告警模式
        8. DB25 Port Open
        9. SELECT ON/OFF
        10. 設定 RF Sensor
        
        Args:
            timeout_per_step: 每步超時時間（預設 5 秒）
        
        Returns:
            是否成功完成
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info("=" * 60)
        logger.info("開始 E84 Initialize 流程")
        logger.info("=" * 60)
        
        try:
            logger.info("[0/10] read_firmware_version")
            if not self.read_firmware_version():
                logger.error("read_firmware_version 失敗")
                return False
            time.sleep(0.2)

            logger.info("[1/10] read_config")
            if not self.read_config():
                logger.error("read_config 失敗")
                return False
            time.sleep(0.2)

            logger.info("[2/10] initialize_timeout_params")
            if not self.initialize_timeout_params():
                logger.error("initialize_timeout_params 失敗")
                return False
            time.sleep(0.2)

            logger.info("[3/10] set_unknown_0x8067")
            if not self.set_unknown_0x8067():
                logger.error("set_unknown_0x8067 失敗")
                return False
            time.sleep(0.2)

            logger.info("[4/10] set_sensor_event")
            if not self.set_sensor_event():
                logger.error("set_sensor_event 失敗")
                return False
            time.sleep(0.2)

            logger.info("[5/10] set_input_timeout")
            if not self.set_input_timeout():
                logger.error("set_input_timeout 失敗")
                return False
            time.sleep(0.2)

            logger.info("[6/10] set_alarm_mode")
            if not self.set_alarm_mode():
                logger.error("set_alarm_mode 失敗")
                return False
            time.sleep(0.2)

            # Step 1: DB25 Port Open
            logger.info("[7/10] DB25 Port Open")
            if not self.db25_port_control(open=True):
                logger.error("DB25 Port Open 失敗")
                return False
            time.sleep(0.2)
            
            # Step 2: SELECT ON
            logger.info("[8/10] SELECT ON")
            if not self.select_control(select_on=True):
                logger.error("SELECT ON 失敗")
                return False
            time.sleep(0.2)
            
            # Step 2-1: SET RF Sensor
            logger.info("[9/10] set_RF_sensor")
            if not self.set_RF_sensor():
                logger.error("set_RF_sensor 失敗")
                return False
            time.sleep(0.2)
            
            # Step 3: SELECT OFF
            logger.info("[10/10] SELECT OFF")
            if not self.select_control(select_on=False):
                logger.error("SELECT OFF 失敗")
                return False
            time.sleep(0.2)

            # 等待必要的訊號
            signals = [
                # ("GO", True),
                ("HOAVBL", True),
                ("ES", True),
            ]
            
            for signal_name, state in signals:
                if not self._wait_for_signal(signal_name, state, timeout_per_step):
                    logger.error(f"等待 {signal_name} 超時")
                    return False
            
            logger.info("=" * 60)
            logger.info("✅ Initialize 流程完成")
            logger.info("=" * 60)
            return True

        except Exception as e:
            logger.error(f"initialize_device 流程異常: {e}", exc_info=True)
            return False

    def db25_port_control(self, open: bool = True) -> bool:
        """
        DB25 Port 控制
        
        Args:
            open: True=打開, False=關閉
        
        Returns:
            是否成功
        """
        param = 0x0001 if open else 0x0000
        response = self._send_e84_command(E84Command.DB25_PORT, param)
        if response:
            logger.info(f"DB25 Port {'打開' if open else '關閉'}")
            return True
        return False
    
    def select_control(self, select_on: bool, go: bool = False, 
                      mode: bool = False, select: bool = True, power: bool = False) -> bool:
        """
        SELECT 控制
        
        Args:
            select_on: True=SELECT ON, False=SELECT OFF
            go: GO bit
            mode: MODE bit
            select: SELECT bit
            power: POWER bit
        
        Returns:
            是否成功
        """
        if select_on:
            # SELECT ON: [0]=GO, [1]=MODE, [2]=SELECT, [3]=POWER
            param = (int(go) << 0) | (int(mode) << 1) | (int(select) << 2) | (int(power) << 3)
        else:
            param = 0x0000
        
        response = self._send_e84_command(E84Command.SELECT_CONTROL, param)
        if response:
            logger.info(f"SELECT {'ON' if select_on else 'OFF'}")
            return True
        return False

    def send_CONT_command(self, cont: int = 0) -> bool:
        """發送 CONT 命令"""
        response = self._send_e84_command(E84Command.CONTINUE, cont)
        if response:
            logger.info("CONT 命令已發送")
            return True
        return False

    def send_CS_command(self, cs: int = 0) -> bool:
        """發送 CS 命令"""
        response = self._send_e84_command(E84Command.CS_SELECT, cs)
        if response:
            logger.info("CS 命令已發送")
            return True
        return False
    
    def send_load_command(self) -> bool:
        """發送 LOAD 命令"""
        response = self._send_e84_command(E84Command.LOAD_UNLOAD, 0x0000)
        if response:
            logger.info("LOAD 命令已發送")
            return True
        return False
    
    def send_unload_command(self) -> bool:
        """發送 UNLOAD 命令"""
        response = self._send_e84_command(E84Command.LOAD_UNLOAD, 0x0001)
        if response:
            logger.info("UNLOAD 命令已發送")
            return True
        return False
    
    def arm_back_complete(self, is_unload: bool = False) -> bool:
        """
        手臂回收完成
        
        Args:
            is_unload: True=Unload 流程, False=Load 流程
        
        Returns:
            是否成功
        """
        param = 0x0001 if is_unload else 0x0001  # 根據協議，兩者都是 0x0001
        response = self._send_e84_command(E84Command.ARM_BACK, param)
        if response:
            logger.info("手臂回收完成")
            return True
        return False
    
    def alarm_reset(self) -> bool:
        """Alarm Reset"""
        response = self._send_e84_command(E84Command.ALARM_RESET, 0x0000)
        if response:
            logger.info("Alarm Reset")
            return True
        return False
    
    # ==================== RF Sensor Integration ====================
    
    def set_RF_sensor(self, rf_port: Optional[str] = None, 
                     medium: CommunicationMedium = CommunicationMedium.WIFI_5G,
                     channel: int = 128, device_id: str = "000120", 
                     port: int = 2) -> bool:
        """
        設定 RF Sensor（使用 SyncRFSensor）
        
        Args:
            rf_port: RF Sensor 串口（None=使用初始化時設定）
            medium: 通訊介質（預設 5G）
            channel: 頻道（預設 128）
            device_id: 設備 ID（預設 "000120"）
            port: 埠號（預設 2）
        
        Returns:
            是否成功
        """
        rf_port = rf_port if rf_port else self._rf_port
        
        print("\n" + "="*60)
        print("RF Sensor - Synchronous Configuration")
        print("="*60 + "\n")
        
        try:
            with SyncRFSensor(rf_port, timeout=5.0, debug=True) as sensor:
                print("✓ Connected to RF sensor\n")
                
                # Set communication medium
                print(f"Setting communication medium to {medium.name}...")
                if sensor.set_communication_medium(medium):
                    print(f"✓ Medium set to {medium.name}\n")
                
                # Set channel
                print(f"Setting channel to {channel}...")
                if sensor.set_channel(channel):
                    print(f"✓ Channel set to {channel}\n")
                
                # Set device ID
                print(f"Setting device ID to {device_id}...")
                if sensor.set_device_id(device_id):
                    print(f"✓ Device ID set\n")
                
                # Set port
                print(f"Setting port to {port}...")
                if sensor.set_port(port):
                    print(f"✓ Port set to {port}\n")
                
                # Check RF status
                print("Checking RF configuration status...")
                if sensor.read_rf_status():
                    print("✓ RF configuration successful!\n")
                    return True
                
                # Read current settings
                print("Reading current configuration:")
                current_medium = sensor.get_communication_medium()
                current_channel = sensor.get_channel()
                current_device_id = sensor.get_device_id()
                current_port = sensor.get_port()
                
                print(f"  Medium:    {current_medium.name if current_medium else 'Unknown'}")
                print(f"  Channel:   {current_channel}")
                print(f"  Device ID: {current_device_id}")
                print(f"  Port:      {current_port}")
                print()
                
                # Print statistics
                sensor.print_statistics()
                
        except ConnectionError as e:
            print(f"✗ Connection error: {e}")
            logger.error(f"RF Sensor 連線錯誤: {e}")
            return False
        except TimeoutError as e:
            print(f"✗ Timeout error: {e}")
            logger.error(f"RF Sensor 超時錯誤: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            logger.error(f"RF Sensor 錯誤: {e}")
            return False

        return False
    
    # ==================== 完整的 Load/Unload 流程 ====================
    
    def _wait_for_signal(
        self, 
        signal_name: str, 
        expected_state: bool, 
        timeout: float = 5.0
    ) -> bool:
        """
        等待特定訊號狀態
        
        Args:
            signal_name: 訊號名稱
            expected_state: 期望狀態 (True=ON, False=OFF)
            timeout: 超時時間（預設 5 秒）
        
        Returns:
            是否收到期望狀態
        """
        logger.debug(f"等待訊號: {signal_name} = {expected_state}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 檢查當前狀態
            current_state = self.get_signal_state(signal_name)
            if current_state == expected_state:
                logger.debug(f"訊號達成: {signal_name} = {expected_state}")
                return True
            
            # 如果有事件佇列，從佇列等待
            if self._event_queue:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        break
                    
                    event = self._event_queue.get(timeout=min(1.0, remaining_time))
                    if event.signal_name == signal_name and E84Signal.is_signal_on(event.code) == expected_state:
                        return True
                except queue.Empty:
                    continue
            else:
                # 沒有佇列，短暫等待
                time.sleep(0.1)
        
        logger.warning(f"等待訊號超時: {signal_name} = {expected_state}")
        return False

    def load(self, timeout_per_step: float = 5.0) -> bool:
        """
        完整的 Load 流程（全自動）
        
        流程步驟：
        1. 發送 CONT 命令
        2. 發送 CS 命令
        3. 發送 LOAD 命令
        4. 等待訊號序列
        5. 等待 L_REQ OFF（可伸出手臂放貨）
        6. 手臂回收完成
        7. 等待完成訊號
        8. Alarm Reset
        
        Args:
            timeout_per_step: 每步超時時間（預設 5 秒）
        
        Returns:
            是否成功完成
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info("=" * 60)
        logger.info("開始 Load 流程")
        logger.info("=" * 60)
        
        try:
            # Step 1: 發送 CONT 命令
            logger.info("[1/8] 發送 CONT 命令")
            if not self.send_CONT_command(cont=0):
                logger.error("CONT 命令失敗")
                return False
            time.sleep(0.2)
            
            logger.info("[2/8] 發送 CS 命令")
            if not self.send_CS_command(cs=0):
                logger.error("CS 命令失敗")
                return False
            time.sleep(0.2)
            
            # Step 2: 發送 LOAD 命令
            logger.info("[3/8] 發送 LOAD 命令")
            if not self.send_load_command():
                logger.error("LOAD 命令失敗")
                return False
            time.sleep(0.2)
            
            # Step 3: 等待訊號序列
            logger.info("[4/8] 等待設備回應訊號...")
            signals = [
                # ("GO", True),
                ("CS_0", True),
                ("VALID", True),
                ("L_REQ", True),
                ("TR_REQ", True),
                ("READY", True),
                ("BUSY", True),
            ]
            
            for signal_name, state in signals:
                if not self._wait_for_signal(signal_name, state, timeout_per_step):
                    logger.error(f"等待 {signal_name} 超時")
                    return False
            
            # Step 4: 等待 L_REQ OFF（可伸出手臂）
            logger.info("[5/8] 等待 L_REQ OFF（可伸出手臂放貨）")
            if not self._wait_for_signal("L_REQ", False, timeout_per_step):
                logger.error("等待 L_REQ OFF 超時")
                return False
            
            logger.info(">>> 現在可以伸出手臂放貨 <<<")
            # 這裡可以加入實際的手臂控制邏輯
            time.sleep(1.0)  # 模擬手臂動作時間
            
            # Step 5: 手臂回收完成
            logger.info("[6/8] 通知手臂回收完成")
            if not self.arm_back_complete(is_unload=False):
                logger.error("ARM Back Complete 失敗")
                return False
            
            # Step 6: 等待完成訊號
            logger.info("[7/8] 等待完成訊號...")
            completion_signals = [
                ("BUSY", False),
                ("TR_REQ", False),
                ("COMPT", True),
                ("READY", False),
                ("VALID", False),
                ("COMPT", False),
                ("CS_0", False),
            ]
            
            for signal_name, state in completion_signals:
                if not self._wait_for_signal(signal_name, state, timeout_per_step):
                    logger.warning(f"等待 {signal_name} 超時（可能不影響流程）")
                    # 不返回 False，繼續流程
            
            # Step 7: Alarm Reset
            logger.info("[8/8] Alarm Reset")
            self.alarm_reset()
            
            logger.info("=" * 60)
            logger.info("✅ Load 流程完成")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Load 流程異常: {e}", exc_info=True)
            return False
    
    def unload(self, timeout_per_step: float = 5.0) -> bool:
        """
        完整的 Unload 流程（全自動）
        
        流程步驟：
        1. DB25 Port Open
        2. SELECT ON
        3. SELECT OFF
        4. 發送 UNLOAD 命令
        5. 等待訊號序列
        6. 等待 U_REQ OFF（可伸出手臂取貨）
        7. 手臂回收完成
        8. 等待完成訊號
        9. Alarm Reset
        
        Args:
            timeout_per_step: 每步超時時間（預設 5 秒）
        
        Returns:
            是否成功完成
        """
        logger.info("=" * 60)
        logger.info("開始 Unload 流程")
        logger.info("=" * 60)
        
        try:
            # Step 1: DB25 Port Open
            logger.info("[1/9] DB25 Port Open")
            if not self.db25_port_control(open=True):
                logger.error("DB25 Port Open 失敗")
                return False
            time.sleep(0.2)
            
            # Step 2: SELECT ON
            logger.info("[2/9] SELECT ON")
            if not self.select_control(select_on=True):
                logger.error("SELECT ON 失敗")
                return False
            time.sleep(0.2)
            
            # Step 3: SELECT OFF
            logger.info("[3/9] SELECT OFF")
            if not self.select_control(select_on=False):
                logger.error("SELECT OFF 失敗")
                return False
            time.sleep(0.2)
            
            # Step 4: 發送 UNLOAD 命令
            logger.info("[4/9] 發送 UNLOAD 命令")
            if not self.send_unload_command():
                logger.error("UNLOAD 命令失敗")
                return False
            
            # Step 5: 等待訊號序列
            logger.info("[5/9] 等待設備回應訊號...")
            signals = [
                ("CS_0", True),
                ("VALID", True),
                ("U_REQ", True),
                ("TR_REQ", True),
                ("READY", True),
                ("BUSY", True),
            ]
            
            for signal_name, state in signals:
                if not self._wait_for_signal(signal_name, state, timeout_per_step):
                    logger.error(f"等待 {signal_name} 超時")
                    return False
            
            # Step 6: 等待 U_REQ OFF（可伸出手臂）
            logger.info("[6/9] 等待 U_REQ OFF（可伸出手臂取貨）")
            if not self._wait_for_signal("U_REQ", False, timeout_per_step):
                logger.error("等待 U_REQ OFF 超時")
                return False
            
            logger.info(">>> 現在可以伸出手臂取貨 <<<")
            # 這裡可以加入實際的手臂控制邏輯
            time.sleep(1.0)  # 模擬手臂動作時間
            
            # Step 7: 手臂回收完成
            logger.info("[7/9] 通知手臂回收完成")
            if not self.arm_back_complete(is_unload=True):
                logger.error("ARM Back Complete 失敗")
                return False
            
            # Step 8: 等待完成訊號
            logger.info("[8/9] 等待完成訊號...")
            completion_signals = [
                ("BUSY", False),
                ("TR_REQ", False),
                ("COMPT", True),
                ("READY", False),
                ("VALID", False),
                ("COMPT", False),
                ("CS_0", False),
            ]
            
            for signal_name, state in completion_signals:
                if not self._wait_for_signal(signal_name, state, timeout_per_step):
                    logger.warning(f"等待 {signal_name} 超時（可能不影響流程）")
                    # 不返回 False，繼續流程
            
            # Step 9: Alarm Reset
            logger.info("[9/9] Alarm Reset")
            self.alarm_reset()
            
            logger.info("=" * 60)
            logger.info("✅ Unload 流程完成")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Unload 流程異常: {e}", exc_info=True)
            return False


# ==================== 主程式 ====================

def main():
    """主程式 - 同步版本範例"""
    
    # 配置
    COM_PORT = "COM14"  # E84 主串口
    RF_PORT = "COM15"   # RF Sensor 串口
    BAUDRATE = 115200
    
    # Callback 用於即時監控
    def quick_monitor(signal: str, state: bool):
        print(f"[即時] {signal}: {'ON' if state else 'OFF'}")
    
    # 配置 logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 使用 context manager
        with ActiveE84(COM_PORT, baudrate=BAUDRATE, rf_port=RF_PORT,
                      on_sensor_event=quick_monitor, event_queue_size=100) as e84:
            
            print("\n" + "="*60)
            print("ActiveE84 Synchronous Demo")
            print("="*60 + "\n")
            
            # 初始化設備
            print("Step 1: 初始化設備...")
            success = e84.initialize_device(timeout_per_step=5.0)
            print(f"Initialize 結果: {'成功 ✓' if success else '失敗 ✗'}\n")
            
            if not success:
                print("初始化失敗，退出程式")
                return
            
            # 執行 Load
            print("Step 2: 執行 Load 流程...")
            success = e84.load(timeout_per_step=5.0)
            print(f"Load 結果: {'成功 ✓' if success else '失敗 ✗'}\n")
            
            if success:
                print("\n✅ Load 流程成功完成！")
                print("可以進行下一步操作...")
            else:
                print("\n❌ Load 流程失敗！")
                print("請檢查設備狀態和日誌")
    
    except KeyboardInterrupt:
        print("\n\n程式已中止")
    except Exception as e:
        print(f"\n執行錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
