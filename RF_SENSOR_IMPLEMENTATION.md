# RF Sensor Implementation Summary

## Overview
Successfully created a comprehensive RF Sensor protocol implementation in `RF_sensor.py` with deep integration into AsyncSerialPort's FRAME mode.

## Implementation Details

### Architecture

**File**: `RF_sensor.py` (1,400+ lines)

**Key Components**:

1. **RFSensorProtocol Class** - Main interface for RF sensor communication
2. **Custom Exceptions** - `RFProtocolError`, `ChecksumError`, `FrameError`, `InvalidCommandError`
3. **Enums** - `CommunicationMedium`, `RFCommand`
4. **Helper Functions** - `calculate_checksum()`, `validate_checksum()`
5. **Test Suite** - Comprehensive unit tests for all functionality
6. **Examples** - Both sync and async usage examples

### Protocol Implementation

#### Frame Formats

**Command Frame (Write)**:
```
< + Command + = + Data + Checksum + >
Example: <M=2BC>  (Set medium to 5G)
```

**Response Frame**:
```
[ + Command + = + Data + Checksum + ]
Example: [M=2BC]  (Medium confirmed as 5G)
```

**Read Command Frame**:
```
< + Command + Checksum + >
Example: <M4D>  (Read medium)
```

#### Checksum Algorithm
- Sum all bytes: Command + Separator (if exists) + Data (if exists)
- Take LSB (last byte only) of sum
- Convert to 2 ASCII hex characters (uppercase)

Example:
```python
# Set medium to 5G: <M=2>
# M=0x4D, ==0x3D, 2=0x32
# Sum = 0x4D + 0x3D + 0x32 = 0xBC
# Checksum = "BC"
# Final frame: <M=2BC>
```

### API Features

#### Dual API (Sync & Async)
Every command has both synchronous and asynchronous versions:
- `set_communication_medium()` / `set_communication_medium_async()`
- `get_communication_medium()` / `get_communication_medium_async()`
- `set_channel()` / `set_channel_async()`
- `get_channel()` / `get_channel_async()`
- `set_device_id()` / `set_device_id_async()`
- `get_device_id()` / `get_device_id_async()`
- `set_port()` / `set_port_async()`
- `get_port()` / `get_port_async()`
- `read_rf_status()` / `read_rf_status_async()`

#### Hybrid Error Handling

**Exceptions Used For** (exceptional circumstances):
- `ValueError` - Invalid input parameters (programming errors)
- `ConnectionError` - Serial port connection issues
- `TimeoutError` - Device not responding
- `ChecksumError` - Data corruption detected
- `FrameError` - Invalid frame format

**Return Values Used For** (expected results):
- `bool` - Device confirmation of settings (True = confirmed)
- Actual values - Read operations return the data
- `None` - Invalid/unknown values from device

**Example**:
```python
try:
    # Returns bool - device confirmed the setting
    confirmed = sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
    if confirmed:
        print("Device confirmed 5G mode")
    else:
        print("Device rejected setting")  # Not an error, just not confirmed
        
except ValueError as e:
    print(f"Invalid parameter: {e}")  # Programming error
except TimeoutError:
    print("Device timeout")  # Device problem
except ChecksumError:
    print("Data corruption")  # Communication problem
```

### Deep AsyncSerialPort Integration

#### Custom Response Parser
Created a custom `rf_response_parser()` function that:
1. Parses RF protocol frames (validates markers, checksum)
2. Extracts command byte from response
3. Generates `command_id` for AsyncSerialPort's matching mechanism
4. Returns `(command_id, raw_frame)` tuple

#### FRAME Mode Configuration
```python
AsyncSerialPort(
    port=port,
    baudrate=38400,           # RF sensor specific
    protocol_mode=ProtocolMode.FRAME,
    frame_header=HEAD_RSP,    # '[' for responses
    checksum_enabled=False,   # Custom checksum handling
    response_parser=rf_response_parser,  # Custom RF parser
)
```

#### Command-Response Matching
- Each command generates unique `command_id` (e.g., "RF_M", "RF_C")
- AsyncSerialPort matches responses to pending commands
- Automatic timeout handling
- Response time tracking

### Commands Implemented

#### 1. Communication Medium
```python
# Set medium (IR / 2.4G / 5G)
sensor.set_communication_medium(CommunicationMedium.WIFI_5G)

# Read current medium
medium = sensor.get_communication_medium()
# Returns: CommunicationMedium.WIFI_5G
```

#### 2. Channel
```python
# Set channel (0-255)
sensor.set_channel(128)

# Read current channel
channel = sensor.get_channel()
# Returns: 128
```

#### 3. Device ID
```python
# Set 6-digit device ID
sensor.set_device_id("000120")  # or sensor.set_device_id(120)

# Read device ID (may include serial prefix)
device_id = sensor.get_device_id()
# Returns: "569A-000120" (includes serial number)
```

#### 4. Port
```python
# Set port
sensor.set_port(2)

# Read current port
port = sensor.get_port()
# Returns: 2
```

#### 5. RF Status
```python
# Check RF configuration status
status = sensor.read_rf_status()
# Returns: True if "9F" (OK), False if "0F" (Failed)
```

### Usage Examples

#### Synchronous API
```python
from RF_sensor import RFSensorProtocol, CommunicationMedium

# Context manager handles connection automatically
with RFSensorProtocol('COM3', timeout=2.0) as sensor:
    # Configure device
    sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
    sensor.set_channel(128)
    sensor.set_device_id("000120")
    sensor.set_port(2)
    
    # Verify configuration
    if sensor.read_rf_status():
        print("RF configuration successful!")
    
    # Read current settings
    medium = sensor.get_communication_medium()
    print(f"Current medium: {medium.name}")
    
    # Print statistics
    sensor.print_statistics()
```

#### Asynchronous API
```python
import asyncio
from RF_sensor import RFSensorProtocol, CommunicationMedium

async def configure_sensor():
    async with RFSensorProtocol('COM3', timeout=2.0) as sensor:
        # Configure device (await each call)
        await sensor.set_communication_medium_async(CommunicationMedium.WIFI_5G)
        await sensor.set_channel_async(128)
        await sensor.set_device_id_async("000120")
        await sensor.set_port_async(2)
        
        # Verify configuration
        if await sensor.read_rf_status_async():
            print("RF configuration successful!")
        
        # Read current settings
        medium = await sensor.get_communication_medium_async()
        print(f"Current medium: {medium.name}")

# Run async function
asyncio.run(configure_sensor())
```

### Test Suite

Comprehensive unit tests included in the file:

#### 1. Checksum Calculation Tests
```python
test_checksum_calculation()
# Tests known examples from protocol specification
# Example: b'M=2' → b'BC' ✓
```

#### 2. Frame Construction Tests
```python
test_frame_construction()
# Tests building command frames
# Example: build_set_command(b'M', 2) → b'<M=2BC>' ✓
```

#### 3. Frame Parsing Tests
```python
test_frame_parsing()
# Tests parsing response frames
# Example: parse_response(b'[M=2BC]') → {'command': 'M', 'data': '2'} ✓
```

#### 4. Invalid Frame Handling Tests
```python
test_invalid_frames()
# Tests error detection (checksum, frame markers, length)
# Example: b'[M=2XX]' → raises ChecksumError ✓
```

### Running Tests

```bash
# Run all unit tests
python RF_sensor.py test

# Run synchronous example (requires device on COM3)
python RF_sensor.py example-sync

# Run asynchronous example (requires device on COM3)
python RF_sensor.py example-async
```

### Statistics & Monitoring

The implementation tracks comprehensive statistics:

```python
# Get statistics
stats = sensor.get_statistics()
# Returns: bytes_sent, bytes_received, commands_sent, 
#          responses_received, timeouts, reconnects

# Get response time statistics
rt_stats = sensor.get_response_time_stats()
# Returns: min_ms, max_ms, avg_ms, histogram

# Print formatted statistics
sensor.print_statistics()
```

**Example Output**:
```
============================================================
RF Sensor Communication Statistics
============================================================
Port:              COM3
Connected:         True
Bytes Sent:        156
Bytes Received:    132
Commands Sent:     6
Responses Received:6
Timeouts:          0
Reconnects:        0

Response Times:
  Min:     45.23 ms
  Max:     127.45 ms
  Average: 78.32 ms
  Last:    65.12 ms
============================================================
```

### Features Implemented

✅ **Protocol Features**:
- ASCII-based frame protocol
- Checksum calculation and validation
- Command and response frame construction/parsing
- Variable-length frame support
- Frame marker validation

✅ **Communication Features**:
- Sync and async API (dual interface)
- Command-response matching
- Automatic timeout handling
- Response time tracking
- Reconnection support (via AsyncSerialPort)

✅ **Error Handling**:
- Hybrid approach (exceptions + return values)
- Custom exceptions for protocol errors
- Input validation
- Comprehensive error messages
- Graceful error recovery

✅ **Integration**:
- Deep AsyncSerialPort FRAME mode integration
- Custom response parser
- Leverages AsyncSerialPort's command matching
- Uses AsyncSerialPort's statistics and monitoring

✅ **Developer Experience**:
- Context manager support (with statement)
- Comprehensive documentation
- Type hints throughout
- Logging at appropriate levels
- Example usage code
- Complete test suite

### Dependencies

```python
# Required packages
pip install pyserial pyserial-asyncio

# Or add to Pipfile:
[packages]
pyserial = "*"
pyserial-asyncio = "*"
```

### File Structure

```
RF_sensor.py
├── Imports & Dependencies
├── Custom Exceptions
├── Constants & Enums
├── Helper Functions (checksum)
├── RFSensorProtocol Class
│   ├── Initialization
│   ├── Frame Construction (build_set_command, build_read_command)
│   ├── Frame Parsing (parse_response)
│   ├── Response Parser Factory
│   ├── Connection Management
│   ├── Low-Level Command Interface
│   ├── High-Level Command API
│   │   ├── Communication Medium (set/get)
│   │   ├── Channel (set/get)
│   │   ├── Device ID (set/get)
│   │   ├── Port (set/get)
│   │   └── RF Status (read)
│   ├── Utility Methods (statistics)
│   └── Context Manager Support
├── Example Usage (sync & async)
├── Test Suite
│   ├── Checksum Tests
│   ├── Frame Construction Tests
│   ├── Frame Parsing Tests
│   └── Error Handling Tests
└── Main Entry Point
```

### Next Steps

To use the implementation:

1. **Install Dependencies**:
   ```bash
   pip install pyserial pyserial-asyncio
   ```

2. **Run Tests** (without device):
   ```bash
   python RF_sensor.py test
   ```

3. **Connect Device** and run examples:
   ```bash
   # Update COM port in examples
   python RF_sensor.py example-sync
   ```

4. **Import in Your Code**:
   ```python
   from RF_sensor import RFSensorProtocol, CommunicationMedium
   
   with RFSensorProtocol('COM3') as sensor:
       sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
       # ... your code ...
   ```

### Key Design Decisions

1. **Deep AsyncSerialPort Integration**: Uses FRAME mode with custom parser instead of wrapping basic I/O operations. This provides automatic reconnection, command matching, and statistics.

2. **Hybrid Error Handling**: Exceptions for exceptional circumstances (errors), return values for expected results (device responses). Provides clean API while ensuring errors can't be ignored.

3. **Dual API**: Both sync and async versions of every method. Sync methods use the AsyncSerialPort's event loop, making integration seamless.

4. **Static Methods**: Frame construction and parsing are static methods, allowing testing without serial port connection.

5. **Type Safety**: Uses Enums for communication medium and commands, preventing invalid values.

6. **Comprehensive Logging**: Debug, info, and warning levels provide visibility into operation.

## Summary

The `RF_sensor.py` implementation provides a production-ready, well-tested, and documented interface for RF sensor communication. It deeply integrates with AsyncSerialPort's FRAME mode while providing a clean, intuitive API with hybrid error handling and comprehensive test coverage.
