"""
Synchronous RF Sensor Protocol Implementation

This module provides a purely synchronous Python interface for communicating with
RF sensor devices using a custom ASCII-based frame protocol over serial port.

Protocol Specifications:
- Serial: 38400 baud, 8N1
- Frame format: ASCII-encoded with checksum validation
- Command frame: < + Command + = + Data + Checksum + >
- Response frame: [ + Command + = + Data + Checksum + ]
- Read frame: < + Command + Checksum + >

Features:
- Pure synchronous API (no async/await)
- Inherits from SyncSerialPort for robust serial communication
- Automatic checksum calculation and validation
- Command/response matching
- Automatic reconnection support
- Comprehensive logging and statistics
- Context manager support

Author: Generated for SmartIO-AGV Project
Date: November 10, 2025
"""

import logging
import sys
from typing import Callable, Optional, Tuple, Dict, Any
from enum import Enum

from sync_serial_gyro import SyncSerialPort, ProtocolMode

COM_PORT = "COM15"  # 根據實際情況修改
BAUDRATE = 38400

# ==================== Custom Exceptions ====================

class RFProtocolError(Exception):
    """Base exception for RF protocol errors"""
    pass


class ChecksumError(RFProtocolError):
    """Checksum validation failed"""
    pass


class FrameError(RFProtocolError):
    """Invalid frame format"""
    pass


class InvalidCommandError(RFProtocolError):
    """Invalid command or parameter"""
    pass


# ==================== Constants ====================

class CommunicationMedium(Enum):
    """Communication medium types"""
    IR = 0
    WIFI_2_4G = 1
    WIFI_5G = 2


class RFCommand(Enum):
    """RF sensor command codes"""
    MEDIUM = b'M'      # Set/Get communication medium
    CHANNEL = b'C'     # Set/Get channel
    ID = b'A'          # Set/Get device ID
    PORT = b'N'        # Set/Get port
    RF_STATUS = b'Y'   # Read RF status


# Frame markers
HEAD_CMD = b'<'       # 0x3C - Command frame header
TAIL_CMD = b'>'       # 0x3E - Command frame tail
HEAD_RSP = b'['       # 0x5B - Response frame header
TAIL_RSP = b']'       # 0x5D - Response frame tail
SEPARATOR = b'='      # 0x3D - Separator between command and data


# ==================== Helper Functions ====================

def calculate_checksum(data_bytes: bytes) -> bytes:
    """
    Calculate checksum for RF sensor protocol.
    
    Per protocol specification:
    - Sum: Command + Separator (if exists) + Setting Data (if exists)
    - Take last byte (LSB) of sum result
    - Convert to 2 ASCII hex characters
    
    Args:
        data_bytes: Bytes to sum (Command + Separator + Data, excluding HEAD and TAIL)
        
    Returns:
        2 ASCII characters representing the last byte in hex (e.g., b'42' for 0x42)
    
    Example:
        >>> calculate_checksum(b'M=2')
        b'BC'
        >>> # 0x4D + 0x3D + 0x32 = 0xBC, formatted as 'BC'
    """
    # Sum all bytes and take last byte only (LSB)
    checksum = sum(data_bytes) & 0xFF
    
    # Convert to 2-character ASCII hex string (uppercase)
    checksum_hex = f"{checksum:02X}"
    
    # Return as bytes
    return checksum_hex.encode('ascii')


def validate_checksum(frame: bytes, received_checksum: bytes) -> bool:
    """
    Validate checksum of received frame.
    
    Args:
        frame: Frame data (without HEAD, TAIL, and checksum)
        received_checksum: Received checksum (2 ASCII hex chars)
        
    Returns:
        True if checksum is valid
    """
    expected_checksum = calculate_checksum(frame)
    return received_checksum.upper() == expected_checksum.upper()


# ==================== SyncRFSensor Class ====================

class SyncRFSensor(SyncSerialPort):
    """
    Synchronous RF Sensor communication class.
    
    This class provides a purely synchronous interface for RF sensor commands,
    inheriting from SyncSerialPort for robust serial communication.
    
    Args:
        port: Serial port name (e.g., "COM3", "/dev/ttyUSB0")
        timeout: Response timeout in seconds (default: 2.0)
        auto_reconnect: Enable automatic reconnection (default: True)
        debug: Enable debug logging (default: False)
        **kwargs: Additional arguments passed to SyncSerialPort
    
    Example:
        >>> # Synchronous usage with context manager
        >>> with SyncRFSensor('COM3') as sensor:
        ...     sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
        ...     status = sensor.read_rf_status()
        ...     print(f"RF Status: {'OK' if status else 'FAILED'}")
        
        >>> # Manual connection management
        >>> sensor = SyncRFSensor('COM3')
        >>> sensor.connect()
        >>> sensor.set_channel(128)
        >>> sensor.disconnect()
    """
    
    def __init__(
        self,
        port: str,
        timeout: float = 2.0,
        auto_reconnect: bool = True,
        debug: bool = False,
        **kwargs
    ):
        """Initialize synchronous RF sensor protocol handler"""
        # Setup logging first
        self._logger = logging.getLogger(f"SyncRFSensor({port})")
        if debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
        
        # Create custom response parser for RF protocol
        response_parser = self._create_response_parser()
        
        # Initialize parent SyncSerialPort with RF-specific configuration
        super().__init__(
            port=port,
            baudrate=38400,  # RF sensor specific
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=timeout,
            write_timeout=timeout,
            auto_reconnect=auto_reconnect,
            response_timeout=timeout,
            response_parser=response_parser,
            protocol_mode=ProtocolMode.FRAME,  # Use FRAME mode
            frame_header=HEAD_RSP,  # Response starts with '['
            frame_length=24,  # Minimum frame length
            checksum_enabled=False,  # We handle checksum ourselves
            max_buffer_size=256,
            **kwargs
        )
        
        self._logger.info(f"SyncRFSensor initialized on {port}")
    
    # ==================== Frame Construction ====================
    
    @staticmethod
    def build_set_command(command_byte: bytes, data_value: Any) -> bytes:
        """
        Build a SET command frame.
        
        Frame format: < + Command + = + Data + Checksum + >
        
        Args:
            command_byte: Single byte command (e.g., b'M', b'C')
            data_value: Numeric value or string to send
            
        Returns:
            Complete command frame as bytes
            
        Example:
            >>> SyncRFSensor.build_set_command(b'M', 2)
            b'<M=2BC>'
        """
        # Convert data to ASCII representation
        if isinstance(data_value, int):
            data_ascii = str(data_value).encode('ascii')
        elif isinstance(data_value, bytes):
            data_ascii = data_value
        else:
            data_ascii = str(data_value).encode('ascii')
        
        # Build message body (for checksum calculation)
        message_body = command_byte + SEPARATOR + data_ascii
        
        # Calculate checksum
        checksum = calculate_checksum(message_body)
        
        # Assemble complete frame
        frame = HEAD_CMD + message_body + checksum + TAIL_CMD
        
        return frame
    
    @staticmethod
    def build_read_command(command_byte: bytes) -> bytes:
        """
        Build a READ command frame (no data).
        
        Frame format: < + Command + Checksum + >
        
        Args:
            command_byte: Single byte command (e.g., b'M', b'C')
            
        Returns:
            Complete command frame as bytes
            
        Example:
            >>> SyncRFSensor.build_read_command(b'M')
            b'<M4D>'
        """
        # Build message body (just command byte for checksum)
        message_body = command_byte
        
        # Calculate checksum
        checksum = calculate_checksum(message_body)
        
        # Assemble complete frame
        frame = HEAD_CMD + message_body + checksum + TAIL_CMD
        
        return frame
    
    # ==================== Frame Parsing ====================
    
    @staticmethod
    def parse_response(response_bytes: bytes) -> Dict[str, Any]:
        """
        Parse response frame and validate.
        
        Frame format: [ + Command + = + Data + Checksum + ]
        
        Args:
            response_bytes: Complete response frame
            
        Returns:
            dict with 'command', 'data', and 'raw' keys
            
        Raises:
            FrameError: Invalid frame format
            ChecksumError: Checksum validation failed
            
        Example:
            >>> SyncRFSensor.parse_response(b'[M=2BC]')
            {'command': 'M', 'data': '2', 'raw': b'[M=2BC]'}
        """
        if len(response_bytes) < 6:
            raise FrameError(f"Response too short: {len(response_bytes)} bytes")
        
        # Validate frame markers
        if response_bytes[0:1] != HEAD_RSP:
            raise FrameError(f"Invalid frame header: {response_bytes[0]:02X} (expected {HEAD_RSP[0]:02X})")
        
        if response_bytes[-1:] != TAIL_RSP:
            raise FrameError(f"Invalid frame tail: {response_bytes[-1]:02X} (expected {TAIL_RSP[0]:02X})")
        
        # Extract command byte
        command = response_bytes[1:2]
        
        # Find separator
        if SEPARATOR in response_bytes:
            sep_idx = response_bytes.index(SEPARATOR)
            
            # Extract data and checksum
            # Format: [CMD=DATA_CHECKSUM]
            # Last 2 bytes before ] are checksum
            data_and_checksum = response_bytes[sep_idx+1:-1]
            
            if len(data_and_checksum) < 2:
                raise FrameError(f"Invalid frame: missing checksum")
            
            data = data_and_checksum[:-2]
            received_checksum = data_and_checksum[-2:]
            
            # Calculate expected checksum (Command + Separator + Data)
            message_body = response_bytes[1:-3]  # Everything except [, checksum, ]
            
            # Validate checksum
            if not validate_checksum(message_body, received_checksum):
                expected = calculate_checksum(message_body)
                raise ChecksumError(
                    f"Checksum mismatch: expected {expected.decode()}, "
                    f"got {received_checksum.decode()}"
                )
            
            return {
                'command': command.decode('ascii'),
                'data': data.decode('ascii'),
                'raw': response_bytes
            }
        else:
            # Read response without data (e.g., ACK only)
            # Format: [CMD_CHECKSUM]
            checksum = response_bytes[-3:-1]  # Last 2 bytes before ]
            message_body = response_bytes[1:-3]  # Command byte only
            
            # Validate checksum
            if not validate_checksum(message_body, checksum):
                expected = calculate_checksum(message_body)
                raise ChecksumError(
                    f"Checksum mismatch: expected {expected.decode()}, "
                    f"got {checksum.decode()}"
                )
            
            return {
                'command': command.decode('ascii'),
                'data': None,
                'raw': response_bytes
            }
    
    def _create_response_parser(self) -> Callable[[bytes], Tuple[Optional[str], bytes]]:
        """
        Create custom response parser for SyncSerialPort integration.

        This parser extracts command_id from RF protocol responses to enable
        command-response matching in SyncSerialPort.

        Returns:
            Callable that takes response bytes and returns (command_id, response_data)
        """
        def rf_response_parser(response: bytes) -> Tuple[Optional[str], bytes]:
            """
            Parse RF protocol response and extract command_id.

            Args:
                response: Raw response bytes (complete frame)

            Returns:
                Tuple[Optional[str], bytes]: (command_id, response_data)
                - command_id: Used for matching with pending commands
                - response_data: Complete frame for further processing
            """
            try:
                # Parse the response
                parsed = self.parse_response(response)

                # Generate command_id from command byte
                # This matches what we'll use when sending commands
                command_id = f"RF_{parsed['command']}"

                self._logger.debug(
                    f"Parsed response: cmd={parsed['command']}, "
                    f"data={parsed['data']}, id={command_id}"
                )

                return command_id, response

            except (FrameError, ChecksumError) as e:
                self._logger.error(f"Response parse error: {e}")
                return None, response
            except Exception as e:
                self._logger.error(f"Unexpected parse error: {e}")
                return None, response

        return rf_response_parser
    
    # ==================== Low-Level Command Interface ====================
    
    def send_rf_command(
        self,
        command_byte: bytes,
        data_value: Optional[Any] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send RF command and wait for response (synchronous).
        
        Args:
            command_byte: Command byte (e.g., b'M')
            data_value: Data to send (None for read commands)
            timeout: Response timeout (None = use default)
            
        Returns:
            Parsed response dict with 'command', 'data', 'raw' keys
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response checksum
            FrameError: Invalid response format
        """
        # Build command frame
        if data_value is not None:
            frame = self.build_set_command(command_byte, data_value)
        else:
            frame = self.build_read_command(command_byte)
        
        # Generate command_id for response matching
        command_id = f"RF_{command_byte.decode('ascii')}"
        
        self._logger.debug(f"Sending command: {frame.hex()} ({frame})")
        
        # Send command and wait for response using parent's method
        response = self.send_command(
            command_id=command_id,
            data=frame,
            timeout=timeout or self.timeout,
            expect_response=True
        )
        
        self._logger.debug(f"Received response: {response}")
        
        # Parse response
        parsed = self.parse_response(response)
        
        # Verify command byte matches
        if parsed['command'] != command_byte.decode('ascii'):
            raise FrameError(
                f"Command mismatch: sent {command_byte.decode()}, "
                f"received {parsed['command']}"
            )
        
        return parsed
    
    # ==================== High-Level Command API ====================
    
    # --- Communication Medium ---
    
    def set_communication_medium(
        self,
        medium: CommunicationMedium,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Set communication medium.
        
        Args:
            medium: Communication medium (IR, WIFI_2_4G, WIFI_5G)
            timeout: Response timeout
            
        Returns:
            True if device confirmed the setting
            
        Raises:
            ValueError: Invalid medium value
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        if not isinstance(medium, CommunicationMedium):
            raise ValueError(f"Invalid medium: {medium}. Must be CommunicationMedium enum")
        
        self._logger.info(f"Setting communication medium to {medium.name} ({medium.value})")
        
        response = self.send_rf_command(
            RFCommand.MEDIUM.value,
            medium.value,
            timeout
        )
        
        # Verify device echoed back the value
        confirmed = response['data'] == str(medium.value)
        
        if confirmed:
            self._logger.info(f"Medium set to {medium.name} - CONFIRMED")
        else:
            self._logger.warning(
                f"Medium set but not confirmed: expected {medium.value}, "
                f"got {response['data']}"
            )
        
        return confirmed
    
    def get_communication_medium(
        self,
        timeout: Optional[float] = None
    ) -> Optional[CommunicationMedium]:
        """
        Get current communication medium.
        
        Args:
            timeout: Response timeout
            
        Returns:
            Current communication medium, or None if invalid
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        self._logger.info("Reading communication medium")
        
        response = self.send_rf_command(
            RFCommand.MEDIUM.value,
            None,  # Read command
            timeout
        )
        
        # Parse medium value
        try:
            medium_value = int(response['data'])
            medium = CommunicationMedium(medium_value)
            self._logger.info(f"Current medium: {medium.name} ({medium.value})")
            return medium
        except (ValueError, KeyError):
            self._logger.error(f"Invalid medium value: {response['data']}")
            return None
    
    # --- Channel ---
    
    def set_channel(
        self,
        channel: int,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Set communication channel.
        
        Args:
            channel: Channel number (0-255)
            timeout: Response timeout
            
        Returns:
            True if device confirmed the setting
            
        Raises:
            ValueError: Invalid channel value
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        if not 0 <= channel <= 255:
            raise ValueError(f"Invalid channel: {channel}. Must be 0-255")
        
        self._logger.info(f"Setting channel to {channel}")
        
        response = self.send_rf_command(
            RFCommand.CHANNEL.value,
            channel,
            timeout
        )
        
        # Verify device echoed back the value
        confirmed = response['data'] == str(channel)
        
        if confirmed:
            self._logger.info(f"Channel set to {channel} - CONFIRMED")
        else:
            self._logger.warning(
                f"Channel set but not confirmed: expected {channel}, "
                f"got {response['data']}"
            )
        
        return confirmed
    
    def get_channel(
        self,
        timeout: Optional[float] = None
    ) -> Optional[int]:
        """
        Get current communication channel.
        
        Args:
            timeout: Response timeout
            
        Returns:
            Current channel number, or None if invalid
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        self._logger.info("Reading channel")
        
        response = self.send_rf_command(
            RFCommand.CHANNEL.value,
            None,  # Read command
            timeout
        )
        
        # Parse channel value
        try:
            channel = int(response['data'])
            self._logger.info(f"Current channel: {channel}")
            return channel
        except (ValueError, KeyError):
            self._logger.error(f"Invalid channel value: {response['data']}")
            return None
    
    # --- Device ID ---
    
    def set_device_id(
        self,
        device_id: Any,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Set device ID.
        
        Args:
            device_id: 6-digit ID (string or int, e.g., "000120" or 120)
            timeout: Response timeout
            
        Returns:
            True if device acknowledged (may include serial number prefix)
            
        Raises:
            ValueError: Invalid device ID format
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        # Format device ID as 6-digit string
        if isinstance(device_id, int):
            device_id_str = f"{device_id:06d}"
        else:
            device_id_str = str(device_id).zfill(6)
        
        if len(device_id_str) != 6 or not device_id_str.isdigit():
            raise ValueError(f"Invalid device ID: {device_id}. Must be 6 digits")
        
        self._logger.info(f"Setting device ID to {device_id_str}")
        
        response = self.send_rf_command(
            RFCommand.ID.value,
            device_id_str,
            timeout
        )
        
        # Response may include serial number prefix (e.g., "569A-000120")
        # Check if our ID is in the response
        confirmed = device_id_str in response['data']
        
        if confirmed:
            self._logger.info(f"Device ID set to {device_id_str} - CONFIRMED")
            self._logger.debug(f"Full response: {response['data']}")
        else:
            self._logger.warning(
                f"Device ID set but not confirmed: expected {device_id_str}, "
                f"got {response['data']}"
            )
        
        return confirmed
    
    def get_device_id(
        self,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        Get current device ID.
        
        Args:
            timeout: Response timeout
            
        Returns:
            Device ID string (may include serial prefix), or None if invalid
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        self._logger.info("Reading device ID")
        
        response = self.send_rf_command(
            RFCommand.ID.value,
            None,  # Read command
            timeout
        )
        
        device_id = response['data']
        self._logger.info(f"Current device ID: {device_id}")
        return device_id
    
    # --- Port ---
    
    def set_port(
        self,
        port: int,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Set port setting.
        
        Args:
            port: Port number
            timeout: Response timeout
            
        Returns:
            True if device confirmed the setting
            
        Raises:
            ValueError: Invalid port value
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        if not isinstance(port, int) or port < 0:
            raise ValueError(f"Invalid port: {port}. Must be non-negative integer")
        
        self._logger.info(f"Setting port to {port}")
        
        response = self.send_rf_command(
            RFCommand.PORT.value,
            port,
            timeout
        )
        
        # Verify device echoed back the value
        confirmed = response['data'] == str(port)
        
        if confirmed:
            self._logger.info(f"Port set to {port} - CONFIRMED")
        else:
            self._logger.warning(
                f"Port set but not confirmed: expected {port}, "
                f"got {response['data']}"
            )
        
        return confirmed
    
    def get_port(
        self,
        timeout: Optional[float] = None
    ) -> Optional[int]:
        """
        Get current port setting.
        
        Args:
            timeout: Response timeout
            
        Returns:
            Current port number, or None if invalid
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        self._logger.info("Reading port")
        
        response = self.send_rf_command(
            RFCommand.PORT.value,
            None,  # Read command
            timeout
        )
        
        # Parse port value
        try:
            port = int(response['data'])
            self._logger.info(f"Current port: {port}")
            return port
        except (ValueError, KeyError):
            self._logger.error(f"Invalid port value: {response['data']}")
            return None
    
    # --- RF Status ---
    
    def read_rf_status(
        self,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Read RF configuration status.
        
        Args:
            timeout: Response timeout
            
        Returns:
            True if RF configuration OK ("9F"), False if failed ("0F")
            
        Raises:
            ConnectionError: Not connected
            TimeoutError: Response timeout
            ChecksumError: Invalid response
        """
        self._logger.info("Reading RF status")
        
        response = self.send_rf_command(
            RFCommand.RF_STATUS.value,
            None,  # Read command
            timeout
        )
        
        # Check status code
        # "9F" = RF SET OK
        # "0F" = RF SET Fail
        status_ok = response['data'].upper() == "9F"
        
        status_str = "OK" if status_ok else "FAILED"
        self._logger.info(f"RF Status: {status_str} (response: {response['data']})")
        
        return status_ok
    
    # ==================== Utility Methods ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get communication statistics from underlying serial port.
        
        Returns:
            Dictionary containing statistics (bytes sent/received, timeouts, etc.)
        """
        return self.statistics
    
    def get_response_time_stats(self) -> Dict[str, Any]:
        """
        Get response time statistics.
        
        Returns:
            Dictionary with response time metrics (min, max, avg, histogram)
        """
        rt_stats = self._stats.get('response_times', {})
        return {
            'min_ms': rt_stats.get('min', float('inf')) * 1000 if rt_stats.get('min', float('inf')) != float('inf') else 0,
            'max_ms': rt_stats.get('max', 0) * 1000,
            'avg_ms': rt_stats.get('avg', 0) * 1000,
            'last_ms': rt_stats.get('last', 0) * 1000,
            'total_count': rt_stats.get('count', 0),
            'histogram': rt_stats.get('histogram', {})
        }
    
    def print_statistics(self):
        """Print communication statistics"""
        stats = self.get_statistics()
        rt_stats = self.get_response_time_stats()
        
        print("\n" + "="*60)
        print("RF Sensor Communication Statistics")
        print("="*60)
        print(f"Port:              {self.port}")
        print(f"Connected:         {self.is_connected}")
        print(f"Bytes Sent:        {stats['bytes_sent']}")
        print(f"Bytes Received:    {stats['bytes_received']}")
        print(f"Commands Sent:     {stats['commands_sent']}")
        print(f"Responses Received:{stats['responses_received']}")
        print(f"Timeouts:          {stats['timeouts']}")
        print(f"Reconnects:        {stats['reconnects']}")
        
        if rt_stats['total_count'] > 0:
            print("\nResponse Times:")
            print(f"  Min:     {rt_stats['min_ms']:.2f} ms")
            print(f"  Max:     {rt_stats['max_ms']:.2f} ms")
            print(f"  Average: {rt_stats['avg_ms']:.2f} ms")
            print(f"  Last:    {rt_stats['last_ms']:.2f} ms")
            
            if rt_stats.get('histogram'):
                print("\n  Distribution:")
                for range_name, count in rt_stats['histogram'].items():
                    print(f"    {range_name}: {count}")
        
        print("="*60 + "\n")
    
    # ==================== Context Manager ====================
    
    def __enter__(self):
        """Sync context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit"""
        self.disconnect()
    
    def __repr__(self):
        return (
            f"SyncRFSensor(port={self.port}, "
            f"connected={self.is_connected})"
        )


# ==================== Example Usage ====================

def example_sync_usage():
    """Example of synchronous API usage"""
    print("\n" + "="*60)
    print("RF Sensor - Synchronous Usage Example")
    print("="*60 + "\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and configure device
    try:
        with SyncRFSensor(COM_PORT, timeout=2.0, debug=True) as sensor:
            print("\n✓ Connected to RF sensor\n")
            
            # 1. Set communication medium to WIFI 5G
            print("1. Setting communication medium to WIFI_5G...")
            if sensor.set_communication_medium(CommunicationMedium.WIFI_5G):
                print("   ✓ Medium set successfully")
            else:
                print("   ✗ Medium set but not confirmed")
            
            # 2. Read back the medium
            print("\n2. Reading communication medium...")
            medium = sensor.get_communication_medium()
            if medium:
                print(f"   ✓ Current medium: {medium.name} ({medium.value})")
            else:
                print("   ✗ Failed to read medium")
            
            # 3. Set channel
            print("\n3. Setting channel to 128...")
            if sensor.set_channel(128):
                print("   ✓ Channel set successfully")
            else:
                print("   ✗ Channel set but not confirmed")
            
            # 4. Read back the channel
            print("\n4. Reading channel...")
            channel = sensor.get_channel()
            if channel is not None:
                print(f"   ✓ Current channel: {channel}")
            else:
                print("   ✗ Failed to read channel")
            
            # 5. Set device ID
            print("\n5. Setting device ID to 000120...")
            if sensor.set_device_id(120):
                print("   ✓ Device ID set successfully")
            else:
                print("   ✗ Device ID set but not confirmed")
            
            # 6. Read back device ID
            print("\n6. Reading device ID...")
            device_id = sensor.get_device_id()
            if device_id:
                print(f"   ✓ Current device ID: {device_id}")
            else:
                print("   ✗ Failed to read device ID")
            
            # 7. Set port
            print("\n7. Setting port to 2...")
            if sensor.set_port(2):
                print("   ✓ Port set successfully")
            else:
                print("   ✗ Port set but not confirmed")
            
            # 8. Read back port
            print("\n8. Reading port...")
            port = sensor.get_port()
            if port is not None:
                print(f"   ✓ Current port: {port}")
            else:
                print("   ✗ Failed to read port")
            
            # 9. Read RF status
            print("\n9. Reading RF status...")
            status = sensor.read_rf_status()
            print(f"   {'✓' if status else '✗'} RF Status: {'OK' if status else 'FAILED'}")
            
            # 10. Print statistics
            print("\n10. Communication Statistics:")
            sensor.print_statistics()
            
            print("\n" + "="*60)
            print("All operations completed successfully!")
            print("="*60 + "\n")
            
    except ConnectionError as e:
        print(f"\n✗ Connection error: {e}")
    except TimeoutError as e:
        print(f"\n✗ Timeout error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


# ==================== Test Cases ====================

def test_checksum_calculation():
    """Test checksum calculation with known examples from protocol doc"""
    print("\n" + "="*60)
    print("Testing Checksum Calculation")
    print("="*60 + "\n")
    
    test_cases = [
        # (data, expected_checksum, description)
        (b'M=2', b'BC', "Set medium to 5G"),
        (b'M', b'4D', "Read medium"),
        (b'C=128', b'1B', "Set channel to 128"),
        (b'N=2', b'BD', "Set port to 2"),
        (b'Y', b'59', "Read RF status"),
    ]
    
    passed = 0
    for data, expected, description in test_cases:
        result = calculate_checksum(data)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}")
        print(f"   Data: {data}, Expected: {expected.decode()}, Got: {result.decode()}")
        if result == expected:
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")


def test_frame_construction():
    """Test frame construction with known examples"""
    print("\n" + "="*60)
    print("Testing Frame Construction")
    print("="*60 + "\n")
    
    test_cases = [
        # (command, data, expected_frame, description)
        (b'M', 2, b'<M=2BC>', "Set medium to 5G"),
        (b'C', 128, b'<C=1281B>', "Set channel to 128"),
        (b'N', 2, b'<N=2BD>', "Set port to 2"),
    ]
    
    passed = 0
    for command, data, expected, description in test_cases:
        result = SyncRFSensor.build_set_command(command, data)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}")
        print(f"   Expected: {expected}, Got: {result}")
        if result == expected:
            passed += 1
        print()
    
    # Test read commands
    read_cases = [
        (b'M', b'<M4D>', "Read medium"),
        (b'Y', b'<Y59>', "Read RF status"),
    ]
    
    for command, expected, description in read_cases:
        result = SyncRFSensor.build_read_command(command)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}")
        print(f"   Expected: {expected}, Got: {result}")
        if result == expected:
            passed += 1
        print()
    
    total = len(test_cases) + len(read_cases)
    print(f"Results: {passed}/{total} tests passed\n")


def test_frame_parsing():
    """Test frame parsing with known examples"""
    print("\n" + "="*60)
    print("Testing Frame Parsing")
    print("="*60 + "\n")
    
    test_cases = [
        # (frame, expected_command, expected_data, description)
        (b'[M=2BC]', 'M', '2', "Medium response"),
        (b'[C=1281B]', 'C', '128', "Channel response"),
        (b'[Y=9F15]', 'Y', '9F', "RF status OK"),
        (b'[Y=0F0C]', 'Y', '0F', "RF status fail"),
    ]
    
    passed = 0
    for frame, exp_cmd, exp_data, description in test_cases:
        try:
            result = SyncRFSensor.parse_response(frame)
            if result['command'] == exp_cmd and result['data'] == exp_data:
                print(f"✓ {description}")
                print(f"   Frame: {frame}")
                print(f"   Command: {result['command']}, Data: {result['data']}")
                passed += 1
            else:
                print(f"✗ {description}")
                print(f"   Expected: cmd={exp_cmd}, data={exp_data}")
                print(f"   Got: cmd={result['command']}, data={result['data']}")
        except Exception as e:
            print(f"✗ {description}")
            print(f"   Error: {e}")
        print()
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")


def test_invalid_frames():
    """Test error handling with invalid frames"""
    print("\n" + "="*60)
    print("Testing Invalid Frame Handling")
    print("="*60 + "\n")
    
    test_cases = [
        (b'[M=2XX]', ChecksumError, "Invalid checksum"),
        (b'<M=2BC>', FrameError, "Wrong frame markers"),
        (b'[M]', FrameError, "Too short"),
        (b'[M=BC]', FrameError, "Missing data or checksum"),
    ]
    
    passed = 0
    for frame, expected_exception, description in test_cases:
        try:
            SyncRFSensor.parse_response(frame)
            print(f"✗ {description}")
            print(f"   Expected {expected_exception.__name__} but got no exception")
        except expected_exception:
            print(f"✓ {description}")
            print(f"   Correctly raised {expected_exception.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {description}")
            print(f"   Expected {expected_exception.__name__} but got {type(e).__name__}: {e}")
        print()
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*60)
    print("RF Sensor Protocol - Unit Tests")
    print("="*60)
    
    test_checksum_calculation()
    test_frame_construction()
    test_frame_parsing()
    test_invalid_frames()
    
    print("="*60)
    print("All tests completed!")
    print("="*60 + "\n")


# ==================== Main ====================

if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Run unit tests
            run_all_tests()
        elif sys.argv[1] == "example":
            # Run example usage
            example_sync_usage()
        else:
            print("Usage:")
            print("  python sync_rf_sensor.py          # Run example usage")
            print("  python sync_rf_sensor.py test     # Run unit tests")
            print("  python sync_rf_sensor.py example  # Run example usage")
    else:
        # Default: run example
        example_sync_usage()
