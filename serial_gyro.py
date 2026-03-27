"""
AsyncSerialPort - 支援 Async/Sync 讀寫，自動重連，Command-Response 匹配

主要功能：
1. Async/Sync 雙介面 API
2. 自動斷線檢測與重連
3. Command-Response 匹配機制
4. 回應時間追蹤與統計
5. 事件回調系統
6. Context Manager 支援

使用範例：
    # Async
    async with AsyncSerialPort("COM3", baudrate=9600) as serial:
        response = await serial.send_command_async("CMD_001", b"GET_STATUS\r\n")
    
    # Sync  
    serial = AsyncSerialPort("COM3", baudrate=9600)
    serial.connect()
    response = serial.send_command("CMD_001", b"GET_STATUS\r\n")
    serial.disconnect()
"""

import asyncio
import serial
import serial_asyncio
import threading
import time
import logging
from typing import Optional, Dict, Callable, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class ConnectionState(Enum):
    """連線狀態"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class ProtocolMode(Enum):
    """協議解析模式"""
    LINE = "line"      # 基於 \r\n 分隔符的文本協議
    FRAME = "frame"    # 基於 Header + Length + Checksum 的二進制協議
    FRAME_FIXED = "frame_fixed"  # 基於固定長度的二進制協議

@dataclass
class PendingCommand:
    """等待回應的命令"""
    command_id: str
    timeout: float
    timestamp: float
    future: asyncio.Future
    data: bytes
    response_time: Optional[float] = None
    completed_at: Optional[float] = None


class AsyncSerialPort:
    """
    混合 Async/Sync 串口類別，支援自動重連和命令回應匹配
    
    Args:
        port: 串口名稱 (例如: "COM3", "/dev/ttyUSB0")
        baudrate: 波特率 (預設: 9600)
        bytesize: 數據位 (預設: 8)
        parity: 校驗位 (預設: None)
        stopbits: 停止位 (預設: 1)
        timeout: 讀取超時 (預設: 1.0 秒)
        write_timeout: 寫入超時 (預設: 1.0 秒)
        auto_reconnect: 是否自動重連 (預設: True)
        reconnect_interval: 重連間隔 (預設: 2.0 秒)
        max_reconnect_attempts: 最大重連次數 (預設: -1 無限重試)
        response_timeout: 命令回應超時 (預設: 5.0 秒)
        on_connected: 連線成功回調
        on_disconnected: 斷線回調
        on_reconnecting: 重連中回調
        response_parser: 自定義回應解析器
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: str = serial.PARITY_NONE,
        stopbits: float = serial.STOPBITS_ONE,
        timeout: float = 1.0,
        write_timeout: float = 1.0,
        # 自動重連設定
        auto_reconnect: bool = True,
        reconnect_interval: float = 2.0,
        max_reconnect_attempts: int = -1,
        # 命令回應設定
        response_timeout: float = 5.0,
        # 回調函數
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        on_reconnecting: Optional[Callable[[], None]] = None,
        # 協議解析器
        response_parser: Optional[Callable[[bytes], Tuple[Optional[str], bytes]]] = None,
        # 協議模式配置（新增）
        protocol_mode: ProtocolMode = ProtocolMode.LINE,
        frame_header: bytes = b'\xAA\x55',
        frame_length: int = 8,
        checksum_enabled: bool = True,
        max_buffer_size: int = 256,
        min_frame_length: int = 6,  # 新增：最小幀長度可配置
    ):
        """初始化串口"""
        # 串口配置
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.write_timeout = write_timeout
        
        # 重連配置
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.response_timeout = response_timeout
        
        # 回調函數
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._on_reconnecting = on_reconnecting
        
        # 協議解析器
        if response_parser is None:
            print("AsyncSerialPort : Using default response parser")
        self._response_parser = response_parser or self._default_response_parser
        
        # 協議模式配置（新增）
        self.protocol_mode = protocol_mode
        self._frame_header = frame_header
        self._frame_length = frame_length
        self._checksum_enabled = checksum_enabled
        self._max_buffer_size = max_buffer_size
        self._min_frame_length = min_frame_length  # 新增：保存最小幀長度
        self._read_buffer = bytearray()  # 用於 FRAME 模式的讀取緩衝區
        
        # 內部狀態
        self._state = ConnectionState.DISCONNECTED
        self._serial: Optional[serial.Serial] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        
        # 待處理命令
        self._pending_commands: Dict[str, PendingCommand] = {}
        self._pending_lock: Optional[asyncio.Lock] = None
        
        # 背景任務
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._timeout_checker_task: Optional[asyncio.Task] = None
        
        # 事件循環管理（用於 sync API）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        
        # 統計資訊
        self._stats = {
            "bytes_sent": 0,
            "bytes_received": 0,
            "commands_sent": 0,
            "responses_received": 0,
            "timeouts": 0,
            "reconnects": 0,
            "response_times": {
                "min": float('inf'),
                "max": 0.0,
                "total": 0.0,
                "count": 0,
                "avg": 0.0,
                "last": 0.0,
                "histogram": {
                    "0-100ms": 0,
                    "100-500ms": 0,
                    "500ms-1s": 0,
                    "1s-2s": 0,
                    "2s+": 0,
                }
            }
        }

        self.DEBUG = False
        
        # Logger
        self._logger = logging.getLogger(f"AsyncSerialPort({port})")
        self._logger.setLevel(logging.DEBUG)
        
        # 啟動背景事件循環
        self._start_event_loop()
    
    # ==================== 生命週期管理 ====================
    
    def _start_event_loop(self):
        """啟動背景事件循環（用於 sync API）"""
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name=f"AsyncSerialPort-{self.port}"
        )
        self._loop_thread.start()
        # 等待事件循環啟動
        time.sleep(0.1)
        
        # 在事件循環中創建 asyncio.Lock
        async def init_lock():
            self._pending_lock = asyncio.Lock()
        
        future = asyncio.run_coroutine_threadsafe(init_lock(), self._loop)
        future.result(timeout=1.0)
    
    def _run_event_loop(self):
        """事件循環線程"""
        asyncio.set_event_loop(self._loop)
        if self._loop is not None:
            self._loop.run_forever()
    
    # ==================== 連線管理 ====================
    
    async def connect_async(self) -> bool:
        """
        Async 連線到串口
        
        Returns:
            bool: 連線是否成功
        """
        if self._state == ConnectionState.CONNECTED:
            self._logger.warning("Already connected")
            return True
        
        try:
            self._state = ConnectionState.CONNECTING
            self._logger.info(f"Connecting to {self.port}...")
            
            # 建立串口連線
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
            )
            
            self._state = ConnectionState.CONNECTED
            self._running = True
            
            # 啟動背景任務
            self._reader_task = asyncio.create_task(self._response_reader_loop())
            self._timeout_checker_task = asyncio.create_task(self._timeout_checker_loop())
            
            if self.auto_reconnect:
                self._reconnect_task = asyncio.create_task(self._auto_reconnect_loop())
            
            self._logger.info(f"Connected to {self.port}")
            
            # 觸發回調
            if self._on_connected:
                try:
                    self._on_connected()
                except Exception as e:
                    self._logger.error(f"Error in on_connected callback: {e}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Connection failed: {e}")
            self._state = ConnectionState.DISCONNECTED
            return False
    
    def connect(self, timeout: float = 10.0) -> bool:
        """
        Sync 連線到串口
        
        Args:
            timeout: 連線超時時間（秒）
            
        Returns:
            bool: 連線是否成功
        """
        future = asyncio.run_coroutine_threadsafe(
            self.connect_async(), self._loop
        )
        return future.result(timeout=timeout)
    
    async def disconnect_async(self):
        """Async 斷線"""
        self._logger.info("Disconnecting...")
        self._running = False
        
        # 取消所有待處理的命令
        if self._pending_lock:
            async with self._pending_lock:
                for pending in self._pending_commands.values():
                    if not pending.future.done():
                        pending.future.set_exception(
                            ConnectionError("Disconnected")
                        )
                self._pending_commands.clear()
        
        # 取消背景任務
        for task in [self._reconnect_task, self._reader_task, self._timeout_checker_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 關閉串口
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        
        self._state = ConnectionState.DISCONNECTED
        self._logger.info("Disconnected")
        
        # 觸發回調
        if self._on_disconnected:
            try:
                self._on_disconnected()
            except Exception as e:
                self._logger.error(f"Error in on_disconnected callback: {e}")
    
    def disconnect(self, timeout: float = 5.0):
        """
        Sync 斷線
        
        Args:
            timeout: 斷線超時時間（秒）
        """
        future = asyncio.run_coroutine_threadsafe(
            self.disconnect_async(), self._loop
        )
        future.result(timeout=timeout)
        
        # 停止事件循環
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
    
    # ==================== 基礎 I/O 操作 ====================
    
    async def write_async(self, data: bytes) -> int:
        """
        Async 寫入數據
        
        Args:
            data: 要寫入的數據
            
        Returns:
            int: 寫入的字節數
            
        Raises:
            ConnectionError: 串口未連線
        """
        if self._state != ConnectionState.CONNECTED:
            raise ConnectionError("Not connected")
        
        try:
            self._writer.write(data)
            await self._writer.drain()
            self._stats["bytes_sent"] += len(data)
            return len(data)
        except Exception as e:
            self._logger.error(f"Write error: {e}")
            await self._handle_disconnection()
            raise
    
    def write(self, data: bytes, timeout: Optional[float] = None) -> int:
        """
        Sync 寫入數據
        
        Args:
            data: 要寫入的數據
            timeout: 寫入超時時間（秒）
            
        Returns:
            int: 寫入的字節數
        """
        timeout = timeout or self.write_timeout
        future = asyncio.run_coroutine_threadsafe(
            self.write_async(data), self._loop
        )
        return future.result(timeout=timeout)
    
    async def read_async(self, size: int = 1) -> bytes:
        """
        Async 讀取數據
        
        Args:
            size: 要讀取的字節數
            
        Returns:
            bytes: 讀取的數據
            
        Raises:
            ConnectionError: 串口未連線
        """
        if self._state != ConnectionState.CONNECTED:
            raise ConnectionError("Not connected")
        
        try:
            data = await self._reader.read(size)
            self._stats["bytes_received"] += len(data)
            return data
        except Exception as e:
            self._logger.error(f"Read error: {e}")
            await self._handle_disconnection()
            raise
    
    def read(self, size: int = 1, timeout: Optional[float] = None) -> bytes:
        """
        Sync 讀取數據
        
        Args:
            size: 要讀取的字節數
            timeout: 讀取超時時間（秒）
            
        Returns:
            bytes: 讀取的數據
        """
        timeout = timeout or self.timeout
        future = asyncio.run_coroutine_threadsafe(
            self.read_async(size), self._loop
        )
        return future.result(timeout=timeout)
    
    async def readline_async(self) -> bytes:
        """
        Async 讀取一行
        
        Returns:
            bytes: 讀取的數據（包含換行符）
            
        Raises:
            ConnectionError: 串口未連線
        """
        if self._state != ConnectionState.CONNECTED:
            raise ConnectionError("Not connected")
        
        try:
            data = await self._reader.readline()
            self._stats["bytes_received"] += len(data)
            return data
        except Exception as e:
            self._logger.error(f"Readline error: {e}")
            await self._handle_disconnection()
            raise
    
    def readline(self, timeout: Optional[float] = None) -> bytes:
        """
        Sync 讀取一行
        
        Args:
            timeout: 讀取超時時間（秒）
            
        Returns:
            bytes: 讀取的數據（包含換行符）
        """
        timeout = timeout or self.timeout
        future = asyncio.run_coroutine_threadsafe(
            self.readline_async(), self._loop
        )
        return future.result(timeout=timeout)
    
    # ==================== 命令-回應匹配機制 ====================
    
    async def send_command_async(
        self,
        command_id: str,
        data: bytes,
        timeout: Optional[float] = None,
        expect_response: bool = True
    ) -> Optional[bytes]:
        """
        Async 發送命令並等待回應（追蹤回應時間）
        
        Args:
            command_id: 命令唯一識別碼
            data: 要發送的數據
            timeout: 等待回應的超時時間（None 使用預設值）
            expect_response: 是否期待回應
            
        Returns:
            Optional[bytes]: 回應數據，或 None（如果不期待回應）
            
        Raises:
            TimeoutError: 超時未收到回應
            ConnectionError: 串口未連線
            ValueError: 重複的 command_id
        """
        if not expect_response:
            await self.write_async(data)
            self._stats["commands_sent"] += 1
            return None
        
        timeout = timeout or self.response_timeout
        
        # 記錄發送時間
        send_time = time.time()
        pending = PendingCommand(
            command_id=command_id,
            timeout=timeout,
            timestamp=send_time,
            future=asyncio.Future(),
            data=data
        )
        
        if not self._pending_lock:
            raise RuntimeError("AsyncSerialPort not properly initialized")
        
        # Acquire lock to ensure thread-safe access to pending commands during command-response matching.
        async with self._pending_lock:
            if command_id in self._pending_commands:
                raise ValueError(f"Command {command_id} already pending")
            self._pending_commands[command_id] = pending
        
        try:
            # 發送命令
            await self.write_async(data)
            self._stats["commands_sent"] += 1
            self._logger.info(f">>>>>>>> Sent command {command_id}")
            if self.DEBUG:
                self._logger.info("========= before =============")
            # 等待回應
            response = await asyncio.wait_for(pending.future, timeout=timeout)
            if self.DEBUG:
                self._logger.info("========= after =============")
            # 計算回應時間
            response_time = time.time() - send_time
            pending.response_time = response_time
            pending.completed_at = time.time()
            
            # 記錄到 log 和統計
            self._log_response_time(command_id, response_time)
            self._update_response_stats(response_time)
            
            self._stats["responses_received"] += 1
            return response
            
        except asyncio.TimeoutError:
            response_time = time.time() - send_time
            self._stats["timeouts"] += 1
            self._logger.warning(
                f"Command {command_id} timeout after {response_time:.3f}s "
                f"(expected within {timeout}s)")
            # 清理
            if self._pending_lock:
                async with self._pending_lock:
                    self._pending_commands.pop(command_id, None)
        except Exception as e:
            self._logger.error(f"Error sending command {command_id}: {e}")
            raise
        finally:
            # 清理
            async with self._pending_lock:
                self._pending_commands.pop(command_id, None)
    
    def send_command(
        self,
        command_id: str,
        data: bytes,
        timeout: Optional[float] = None
    ) -> bytes:
        """
        Sync 發送命令並等待回應
        
        Args:
            command_id: 命令唯一識別碼
            data: 要發送的數據
            timeout: 等待回應的超時時間（None 使用預設值）
            
        Returns:
            bytes: 回應數據
            
        Raises:
            TimeoutError: 超時未收到回應
            ConnectionError: 串口未連線
            ValueError: 重複的 command_id
        """
        timeout = timeout or self.response_timeout
        future = asyncio.run_coroutine_threadsafe(
            self.send_command_async(command_id, data, timeout),
            self._loop
        )
        return future.result(timeout=timeout + 1.0)
    
    # ==================== 回應時間追蹤 ====================
    
    def _log_response_time(self, command_id: str, response_time: float):
        """
        記錄命令回應時間到 log
        
        Args:
            command_id: 命令 ID
            response_time: 回應時間（秒）
        """
        # 根據回應時間使用不同的 log level
        if response_time < 0.1:
            level = logging.DEBUG
            status = "FAST"
        elif response_time < 0.5:
            level = logging.INFO
            status = "NORMAL"
        elif response_time < 2.0:
            level = logging.WARNING
            status = "SLOW"
        else:
            level = logging.WARNING
            status = "VERY SLOW"
        
        self._logger.log(
            level,
            f"[{status}] <<<<<<<<< Command {command_id} response time: {response_time*1000:.2f}ms"
        )
    
    def _update_response_stats(self, response_time: float):
        """
        更新回應時間統計
        
        Args:
            response_time: 回應時間（秒）
        """
        rt_stats = self._stats["response_times"]
        
        # 更新統計
        rt_stats["min"] = min(rt_stats["min"], response_time)
        rt_stats["max"] = max(rt_stats["max"], response_time)
        rt_stats["total"] += response_time
        rt_stats["count"] += 1
        rt_stats["avg"] = rt_stats["total"] / rt_stats["count"]
        rt_stats["last"] = response_time
        
        # 更新直方圖
        if response_time < 0.1:
            rt_stats["histogram"]["0-100ms"] += 1
        elif response_time < 0.5:
            rt_stats["histogram"]["100-500ms"] += 1
        elif response_time < 1.0:
            rt_stats["histogram"]["500ms-1s"] += 1
        elif response_time < 2.0:
            rt_stats["histogram"]["1s-2s"] += 1
        else:
            rt_stats["histogram"]["2s+"] += 1
    
    def get_response_time_stats(self) -> dict:
        """
        獲取回應時間統計資訊
        
        Returns:
            dict: 包含回應時間統計的字典
        """
        rt_stats = self._stats["response_times"]
        
        if rt_stats["count"] == 0:
            return {
                "min_ms": 0,
                "max_ms": 0,
                "avg_ms": 0,
                "last_ms": 0,
                "total_count": 0,
                "histogram": {k: 0 for k in rt_stats["histogram"]},
            }
        
        return {
            "min_ms": rt_stats["min"] * 1000 if rt_stats["min"] != float('inf') else 0,
            "max_ms": rt_stats["max"] * 1000,
            "avg_ms": rt_stats["avg"] * 1000,
            "last_ms": rt_stats["last"] * 1000,
            "total_count": rt_stats["count"],
            "histogram": rt_stats["histogram"].copy(),
        }
    
    def print_response_time_stats(self):
        """打印回應時間統計報告"""
        stats = self.get_response_time_stats()
        
        if stats["total_count"] == 0:
            print("No response time data available")
            return
        
        print("\n" + "="*50)
        print("Response Time Statistics")
        print("="*50)
        print(f"Total Commands:  {stats['total_count']}")
        print(f"Min Time:        {stats['min_ms']:.2f} ms")
        print(f"Max Time:        {stats['max_ms']:.2f} ms")
        print(f"Average Time:    {stats['avg_ms']:.2f} ms")
        print(f"Last Time:       {stats['last_ms']:.2f} ms")
        print("\nDistribution:")
        for range_name, count in stats['histogram'].items():
            percentage = (count / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"  {range_name:12} : {count:4d} ({percentage:5.1f}%) {bar}")
        print("="*50 + "\n")
    
    # ==================== 背景任務 ====================
    
    async def _response_reader_loop(self):
        """背景任務：持續讀取串口數據並分發回應"""
        self._logger.info("Response reader started")
        
        while self._running:
            try:
                if self.DEBUG:
                    self._logger.info("==== reader loop A ====")
                if self._state != ConnectionState.CONNECTED:
                    await asyncio.sleep(0.1)
                    continue
                
                # 讀取回應
                response = await self._read_response()
                if self.DEBUG:
                    self._logger.info("==== reader loop B ====")
                
                if response:
                    # 解析 command_id（根據協議模式選擇解析器）
                    if self.protocol_mode == ProtocolMode.FRAME and not self._response_parser:
                        # FRAME 模式且沒有自定義解析器，使用預設幀解析器
                        command_id, response_data = self._default_frame_parser(response)
                    else:
                        # 使用配置的解析器（LINE 模式或自定義解析器）
                        command_id, response_data = self._response_parser(response)
                    
                    if command_id:
                        if command_id == 'E84_0070' or command_id == 'E84_0071':
                            if self.DEBUG:
                                self._logger.info("==== reader loop C ====")
                            continue
                        else:
                            # 分發回應
                            await self._dispatch_response(command_id, response_data)
                    else:
                        # 未識別的回應
                        self._logger.debug(f"Unsolicited response: {response[:50]}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in response reader: {e}")
                await asyncio.sleep(0.1)
        
        self._logger.info("Response reader stopped")
    
    async def _read_response(self) -> Optional[bytes]:
        """
        讀取一個完整的回應
        
        根據 protocol_mode 選擇不同的讀取方式：
        - LINE 模式: 讀取一行（到 \r\n）
        - FRAME 模式: 讀取一個完整的幀
        
        Returns:
            Optional[bytes]: 回應數據，或 None
        """
        try:
            if self.protocol_mode == ProtocolMode.LINE:
                # LINE 模式：讀取一行
                return await self.readline_async()
            elif self.protocol_mode == ProtocolMode.FRAME:
                # FRAME 模式：讀取一個幀
                return await self._read_frame_async()
            elif self.protocol_mode == ProtocolMode.FRAME_FIXED:
                # FRAME_FIXED 模式：讀取一個固定長度的幀
                return await self._read_frame_async_fixed_length()
            else:
                self._logger.error(f"Unknown protocol mode: {self.protocol_mode}")
                return None
        except Exception as e:
            self._logger.debug(f"Error in _read_response: {e}")
            return None
    
    def _default_response_parser(self, response: bytes) -> Tuple[Optional[str], bytes]:
        """
        預設回應解析器（LINE 模式）
        
        格式假設: b"RESPONSE:command_id:data\r\n"
        
        需要根據實際協議覆寫此方法或提供自定義 response_parser
        
        Args:
            response: 原始回應數據
            
        Returns:
            Tuple[Optional[str], bytes]: (command_id, response_data)
        """
        try:
            # 移除換行符
            response = response.rstrip(b'\r\n')
            
            # 分割
            parts = response.split(b':', 2)
            if len(parts) >= 2 and parts[0] == b'RESPONSE':
                command_id = parts[1].decode('utf-8')
                data = parts[2] if len(parts) > 2 else b''
                return command_id, data
                
        except Exception as e:
            self._logger.debug(f"Parse error: {e}")
        
        return None, response
    
    def _default_frame_parser(self, frame: bytes) -> Tuple[Optional[str], bytes]:
        """
        預設幀格式解析器（FRAME 模式）
        
        預設假設幀格式: [Header(2 bytes), cmd_id(1 byte), data(...), checksum(1 byte)]
        
        可以通過提供自定義 response_parser 來覆寫此行為
        
        Args:
            frame: 完整的幀數據
            
        Returns:
            Tuple[Optional[str], bytes]: (command_id, frame_data)
        """
        try:
            if len(frame) >= 3:
                # 假設第 3 個字節是命令 ID
                cmd_id = f"CMD_{frame[2]:02X}"
                return cmd_id, frame
        except Exception as e:
            self._logger.debug(f"Frame parse error: {e}")
        
        return None, frame
    
    def _validate_checksum(self, frame: bytes) -> bool:
        """
        驗證幀的 Checksum
        
        預設算法: sum(frame[:-1]) % 256 == frame[-1]
        
        可以通過繼承此類並覆寫此方法來支援不同的 Checksum 算法
        
        Args:
            frame: 完整的幀數據（包含 checksum）
            
        Returns:
            bool: Checksum 是否有效
        """
        if not self._checksum_enabled or len(frame) < 2:
            return True
        
        try:
            checksum_calculated = sum(frame[:-1]) % 256
            checksum_received = frame[-1]
            return checksum_calculated == checksum_received
        except Exception as e:
            self._logger.error(f"Checksum validation error: {e}")
            return False
    
    async def _read_frame_async_fixed_length(self) -> Optional[bytes]:
        """
        從緩衝區讀取並解析一個完整的幀（FRAME 模式專用）
        
        流程：
        1. 讀取數據到緩衝區（每次最多 64 字節）
        2. 尋找幀頭標記 (例如: 0xAA55)
        3. 檢查是否有完整幀（根據 frame_length）
        4. 驗證 Checksum（如果啟用）
        5. 返回有效幀，丟棄無效數據
        
        Returns:
            Optional[bytes]: 完整且有效的幀，或 None
        """
        try:
            # 檢查是否有完整幀
            if len(self._read_buffer) >= self._frame_length:
                # 提取幀
                frame = bytes(self._read_buffer[:self._frame_length])
                
                # 驗證 Checksum
                if self._validate_checksum(frame):
                    # 有效幀
                    # if self.DEBUG:
                    #     self._logger.debug(f"Valid frame received: {frame.hex()}")
                    # 從緩衝區移除已處理的幀
                    self._read_buffer = self._read_buffer[self._frame_length:]
                    return frame
                else:
                    # 無效 Checksum
                    checksum_calc = sum(frame[:-1]) % 256
                    checksum_recv = frame[-1]
                    self._logger.warning(
                        f"Invalid frame (checksum mismatch - calc: 0x{checksum_calc:02X}, "
                        f"recv: 0x{checksum_recv:02X}): {frame.hex()}"
                    )
                    # 跳過幀頭，繼續尋找下一個幀
                    self._read_buffer = self._read_buffer[len(self._frame_header):]

            # 讀取數據到緩衝區（每次最多 64 bytes）
            chunk = await self.read_async(64)
            if chunk:
                self._read_buffer.extend(chunk)
                self._logger.info(f"_read_frame_async_fixed_length Read {len(chunk)} bytes: {chunk.hex()}")
            
            # 處理緩衝區中的完整幀
            while len(self._read_buffer) >= self._frame_length:
                # 尋找幀頭標記
                start_idx = self._read_buffer.find(self._frame_header)
                
                if start_idx == -1:
                    # 沒有找到有效的幀頭標記
                    if len(self._read_buffer) > len(self._frame_header):
                        # 記錄丟棄的字節（保留最後幾個字節，可能是部分幀頭）
                        keep_bytes = len(self._frame_header) - 1
                        discarded = bytes(self._read_buffer[:-keep_bytes])
                        if discarded:
                            self._logger.debug(
                                f"Discarding {len(discarded)} bytes (no frame start): {discarded.hex()}"
                            )
                        self._read_buffer = self._read_buffer[-keep_bytes:]
                    break
                
                # 移除幀頭之前的字節
                if start_idx > 0:
                    discarded = bytes(self._read_buffer[:start_idx])
                    self._logger.debug(
                        f"Discarding {start_idx} bytes before frame start: {discarded.hex()}"
                    )
                    self._read_buffer = self._read_buffer[start_idx:]
                
                # 檢查是否有完整幀
                if len(self._read_buffer) >= self._frame_length:
                    # 提取幀
                    frame = bytes(self._read_buffer[:self._frame_length])
                    
                    # 驗證 Checksum
                    if self._validate_checksum(frame):
                        # 有效幀
                        # if self.DEBUG:
                        #     self._logger.debug(f"Valid frame received: {frame.hex()}")
                        # 從緩衝區移除已處理的幀
                        self._read_buffer = self._read_buffer[self._frame_length:]
                        return frame
                    else:
                        # 無效 Checksum
                        checksum_calc = sum(frame[:-1]) % 256
                        checksum_recv = frame[-1]
                        self._logger.warning(
                            f"Invalid frame (checksum mismatch - calc: 0x{checksum_calc:02X}, "
                            f"recv: 0x{checksum_recv:02X}): {frame.hex()}"
                        )
                        # 跳過幀頭，繼續尋找下一個幀
                        self._read_buffer = self._read_buffer[len(self._frame_header):]
                else:
                    # 數據不足，等待更多數據
                    break
            
            # 防止緩衝區無限增長
            if len(self._read_buffer) > self._max_buffer_size:
                excess_bytes = len(self._read_buffer) - self._frame_length
                if excess_bytes > 0:
                    discarded = bytes(self._read_buffer[:excess_bytes])
                    self._logger.warning(
                        f"Buffer overflow, clearing {excess_bytes} bytes: {discarded.hex()}"
                    )
                    self._read_buffer = self._read_buffer[-self._frame_length:]
            
            return None
            
        except Exception as e:
            self._logger.error(
                f"Error in _read_frame_async_fixed_length ({type(e).__name__}): {e} | Buffer: {self._read_buffer.hex()}"
            )
            return None
    
    async def _read_frame_async(self) -> Optional[bytes]:
        """
        Read and parse a complete frame (modified for variable-length RF protocol).
        
        For RF sensor: Frames start with head ('<' or '[') and end with tail ('>' or ']').
        Read until tail marker is found, ignoring fixed frame_length.
        """
        try:
            # Read data into buffer (same as before)
            chunk = await self.read_async(64)
            if chunk:
                self._read_buffer.extend(chunk)
                # print(f"DEBUG: _read_frame_async Read {len(chunk)} bytes: {chunk.hex()}")
                self._logger.info(f"_read_frame_async Read {len(chunk)} bytes: {chunk.hex()}")
            
            # Process complete frames
            while len(self._read_buffer) >= len(self._frame_header) + 1:  # At least head + 1 byte
                # Find frame start
                start_idx = self._read_buffer.find(self._frame_header)
                if start_idx == -1:
                    # No header found - discard up to potential partial header
                    keep_bytes = len(self._frame_header) - 1
                    if len(self._read_buffer) > keep_bytes:
                        discarded = bytes(self._read_buffer[:-keep_bytes])
                        self._logger.debug(f"Discarding {len(discarded)} bytes (no frame start): {discarded.hex()}")
                        self._read_buffer = self._read_buffer[-keep_bytes:]
                    break
                
                # Remove data before header
                if start_idx > 0:
                    discarded = bytes(self._read_buffer[:start_idx])
                    self._logger.debug(f"Discarding {start_idx} bytes before frame start: {discarded.hex()}")
                    self._read_buffer = self._read_buffer[start_idx:]
                
                # Determine tail marker based on head
                head_byte = self._read_buffer[0:1]
                if head_byte == b'<':
                    tail_marker = b'>'
                elif head_byte == b'[':
                    tail_marker = b']'
                else:
                    # Invalid head - skip it
                    self._read_buffer = self._read_buffer[1:]
                    continue
                
                # Find tail marker
                tail_idx = self._read_buffer.find(tail_marker, len(self._frame_header))
                if tail_idx == -1:
                    # Tail not found yet - wait for more data
                    break
                # Extract frame (from head to tail inclusive)
                # '+1' is needed to include the tail marker in the frame
                frame_length = tail_idx + 1
                frame = bytes(self._read_buffer[:frame_length])
                
                # Validate minimum length and checksum (if enabled)
                if len(frame) >= self._min_frame_length and (not self._checksum_enabled or self._validate_checksum(frame)):
                    # if self.DEBUG:
                    #     self._logger.debug(f"Valid frame received: {frame.hex()}")
                    self._read_buffer = self._read_buffer[frame_length:]
                    return frame
                else:
                    # Invalid frame - skip head and continue
                    self._logger.warning(f"Invalid frame: {frame.hex()}")
            # Prevent buffer overflow
            if len(self._read_buffer) > self._max_buffer_size:
                # Use a protocol-specific minimum frame size for trimming (e.g., 32 bytes)
                min_frame_size = 32
                excess = len(self._read_buffer) - min_frame_size
                if excess > 0:
                    discarded = bytes(self._read_buffer[:excess])
                    self._logger.warning(f"Buffer overflow, clearing {excess} bytes: {discarded.hex()}")
                    self._read_buffer = self._read_buffer[-min_frame_size:]
            
            return None
            
            return None
        except Exception as e:
            self._logger.error(f"Error in _read_frame_async: {e}")
            return None

    async def _dispatch_response(self, command_id: str, response: bytes):
        """
        將回應分發給等待的命令（記錄回應時間）
        
        Args:
            command_id: 命令 ID
            response: 回應數據
        """
        receive_time = time.time()
        
        async with self._pending_lock:
            pending = self._pending_commands.get(command_id)
            
            if pending and not pending.future.done():
                # 計算回應時間
                response_time = receive_time - pending.timestamp
                pending.response_time = response_time
                pending.completed_at = receive_time
                
                # 設置結果
                pending.future.set_result(response)
                if not self.DEBUG:
                    self._logger.debug(
                        f"Dispatched response to {command_id} "
                        f"(response time: {response_time*1000:.2f}ms)"
                    )
            else:
                self._logger.warning(
                    f"Received response for unknown/completed command: {command_id} {response.hex()}"
                )
    
    async def _timeout_checker_loop(self):
        """定期檢查超時的命令"""
        self._logger.info("Timeout checker started")
        
        while self._running:
            await asyncio.sleep(0.5)
            
            current_time = time.time()
            async with self._pending_lock:
                expired = [
                    cmd_id for cmd_id, pending in self._pending_commands.items()
                    if current_time - pending.timestamp > pending.timeout
                    and not pending.future.done()
                ]
                
                for cmd_id in expired:
                    pending = self._pending_commands[cmd_id]
                    if not pending.future.done():
                        pending.future.set_exception(
                            TimeoutError(f"Command {cmd_id} timeout")
                        )
                        self._logger.warning(f"Command {cmd_id} marked as timeout")
        
        self._logger.info("Timeout checker stopped")
    
    async def _auto_reconnect_loop(self):
        """自動重連任務"""
        self._logger.info("Auto-reconnect enabled")
        attempts = 0
        
        while self._running:
            await asyncio.sleep(1.0)
            
            if self._state == ConnectionState.CONNECTED:
                attempts = 0
                continue
            
            if self._state == ConnectionState.RECONNECTING:
                continue
            
            # 檢查是否超過最大重試次數
            if self.max_reconnect_attempts > 0 and attempts >= self.max_reconnect_attempts:
                self._logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
                break
            
            # 嘗試重連
            attempts += 1
            self._state = ConnectionState.RECONNECTING
            self._logger.info(f"Reconnecting... (attempt {attempts})")
            
            if self._on_reconnecting:
                try:
                    self._on_reconnecting()
                except Exception as e:
                    self._logger.error(f"Error in on_reconnecting callback: {e}")
            
            success = await self.connect_async()
            
            if success:
                self._stats["reconnects"] += 1
                self._logger.info("Reconnection successful")
                attempts = 0
            else:
                await asyncio.sleep(self.reconnect_interval)
    
    async def _handle_disconnection(self):
        """處理斷線"""
        if self._state == ConnectionState.CONNECTED:
            self._logger.warning("Connection lost")
            self._state = ConnectionState.DISCONNECTED
            
            if self._on_disconnected:
                try:
                    self._on_disconnected()
                except Exception as e:
                    self._logger.error(f"Error in on_disconnected callback: {e}")
    
    # ==================== Context Manager ====================
    
    async def __aenter__(self):
        """Async context manager 進入"""
        await self.connect_async()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager 退出"""
        await self.disconnect_async()
    
    def __enter__(self):
        """Sync context manager 進入"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager 退出"""
        self.disconnect()
    
    # ==================== Properties ====================
    
    @property
    def is_connected(self) -> bool:
        """是否已連線"""
        return self._state == ConnectionState.CONNECTED
    
    @property
    def state(self) -> ConnectionState:
        """當前連線狀態"""
        return self._state
    
    @property
    def statistics(self) -> dict:
        """
        獲取統計資訊
        
        Returns:
            dict: 包含所有統計資訊的字典
        """
        return self._stats.copy()
    
    def __repr__(self):
        return (
            f"AsyncSerialPort(port={self.port}, baudrate={self.baudrate}, "
            f"state={self._state.value})"
        )
    
    def __del__(self):
        """析構函數"""
        # 嘗試清理資源
        try:
            if self._running:
                self._running = False
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
        except:
            pass
