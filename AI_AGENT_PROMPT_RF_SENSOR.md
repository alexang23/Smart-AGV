# AI Agent Prompt: RF Sensor Serial Communication Protocol

## Overview
You are tasked with implementing a Python class to communicate with an RF sensor device over a serial port. The device uses a custom frame-based protocol with ASCII-encoded commands and checksum validation.

## Serial Port Configuration
```
Baudrate: 38400
Data bits: 8
Parity: None
Stop bits: 1
```

## Protocol Specification

### Message Frame Structure

#### Command Frame (Write)
```
[HEAD] [COMMAND] [SEPARATOR] [DATA] [CHECKSUM] [TAIL]
  0x3C   1 byte      0x3D     N bytes   2 bytes   0x3E
  '<'                 '='                          '>'
```

#### Response Frame
```
[HEAD] [COMMAND] [SEPARATOR] [DATA] [CHECKSUM] [TAIL]
  0x5B   1 byte      0x3D     N bytes   2 bytes   0x5D
  '['                 '='                          ']'
```

#### Read Command Frame (No Data)
```
[HEAD] [COMMAND] [CHECKSUM] [TAIL]
  0x3C   1 byte    2 bytes    0x3E
  '<'                         '>'
```

### Important Protocol Rules

1. **All data is ASCII-encoded**:
   - Numeric values are converted to ASCII hex representation
   - Example: Value `2` → ASCII `0x32` (character '2')
   - Example: Value `128` → ASCII `0x31 0x32 0x38` (characters '128')

2. **Checksum Calculation**:
   - Sum all bytes: Command + Separator (if exists) + Setting Data (if exists)
   - Take the **last byte only** (LSB) of the sum result
   - Convert that single byte to 2 ASCII hex characters
   - Example: If last byte of sum is `0x42`, checksum is `0x34 0x32` (ASCII '4' '2' representing "42")

3. **Frame Markers**:
   - Command HEAD: `0x3C` ('<')
   - Command TAIL: `0x3E` ('>')
   - Response HEAD: `0x5B` ('[')
   - Response TAIL: `0x5D` (']')
   - Separator: `0x3D` ('=')

## Command Reference

### 1. Set Communication Medium (Command: 'M' / 0x4D)
**Purpose**: Configure communication medium (IR/2.4G/5G)

**Values**:
- `0` = IR
- `1` = 2.4G
- `2` = 5G

**Example - Set to 5G (value 2)**:
```
Write:    3C 4D 3D 32 4243 3E
          <  M  =  2  BC    >
Response: 5B 4D 3D 32 4243 5D
          [  M  =  2  BC    ]
```

**Breakdown**:
- HEAD: `0x3C`
- Command: `0x4D` ('M')
- Separator: `0x3D` ('=')
- Data: `0x32` ('2' in ASCII)
- Checksum: `0x42 0x43` ('BC' - last byte of sum: 0x4D + 0x3D + 0x32 = 0xBC, converted to ASCII "BC")
- TAIL: `0x3E`

### 2. Read Communication Medium (Command: 'M' / 0x4D)
**Purpose**: Read current communication medium setting

**Example**:
```
Write:    3C 4D 3444 3E
          <  M  4D   >
Response: 5B 4D 3D 32 4243 5D
          [  M  =  2  BC    ]
```

**Note**: Read commands have no separator or data field, only HEAD + COMMAND + CHECKSUM + TAIL

### 3. Set Channel (Command: 'C' / 0x43)
**Purpose**: Configure communication channel

**Range**: 0-255 (0x00-0xFF)

**Example - Set to channel 128**:
```
Write:    3C 43 3D 31 32 38 3142 3E
          <  C  =  1  2  8  1B    >
Response: 5B 43 3D 31 32 38 3142 5D
          [  C  =  1  2  8  1B    ]
```

**Breakdown**:
- Data: `0x31 0x32 0x38` (ASCII "128")
- Checksum: `0x31 0x42` (ASCII "1B" - last byte of sum: 0x43 + 0x3D + 0x31 + 0x32 + 0x38 = 0x011B, last byte = 0x1B)

### 4. Set ID (Command: 'A' / 0x41)
**Purpose**: Configure device ID

**Format**: 6-digit numeric ID (000000-999999)

**Example - Set ID to 000120**:
```
Write:    3C 41 3D 30 30 30 31 32 30 4131 3E
          <  A  =  0  0  0  1  2  0  A1    >
Response: 5B 41 3D 35 36 39 41 2D 30 30 30 31 32 30 4233 5D
          [  A  =  5  6  9  A  -  0  0  0  1  2  0  B3    ]
```

**Note**: Response includes device serial number prefix (e.g., "569A-") before the ID

### 5. Set Port (Command: 'N' / 0x4E)
**Purpose**: Configure port setting

**Example - Set to port 2**:
```
Write:    3C 4E 3D 32 4244 3E
          <  N  =  2  BD    >
Response: 5B 4E 3D 32 4244 5D
          [  N  =  2  BD    ]
```

### 6. Read RF Setting Status (Command: 'Y' / 0x59)
**Purpose**: Verify RF configuration status

**Example - Query RF status**:
```
Write:    3C 59 3539 3E
          <  Y  59   >
```

**Success Response**:
```
Response: 5B 59 3D 39 46 3135 5D
          [  Y  =  9  F  15    ]
          Data: "9F" = RF SET OK
```

**Failure Response**:
```
Response: 5B 59 3D 30 46 3043 5D
          [  Y  =  0  F  0C    ]
          Data: "0F" = RF SET Fail
```

## Implementation Requirements

### Class Structure
Create a Python class `RFSensorProtocol` with the following capabilities:

1. **Serial Port Management**:
   - Initialize with port name and timeout
   - Open/close connection methods
   - Context manager support (with statement)

2. **Message Construction**:
   - Method to build command frames
   - Method to build read request frames
   - Automatic checksum calculation
   - ASCII encoding of numeric values

3. **Message Parsing**:
   - Validate response frame structure
   - Extract command and data fields
   - Verify checksum
   - Decode ASCII data to numeric values

4. **Command Methods**:
   - `set_communication_medium(medium)` - medium: 0, 1, or 2
   - `get_communication_medium()` - returns current medium
   - `set_channel(channel)` - channel: 0-255
   - `set_device_id(device_id)` - device_id: 6-digit string or int
   - `set_port(port)` - port: numeric value
   - `read_rf_status()` - returns True (OK) or False (Fail)

5. **Error Handling**:
   - Invalid checksum exception
   - Timeout exception
   - Invalid response format exception
   - Serial port communication errors

### Checksum Calculation Algorithm

```python
def calculate_checksum(data_bytes):
    """
    Calculate checksum for RF sensor protocol.
    
    Per protocol specification:
    - Sum: Command + Separator (if exists) + Setting Data (if exists)
    - Take last byte (LSB) of sum result
    - Convert to 2 ASCII hex characters
    
    Args:
        data_bytes: bytes to sum (Command + Separator + Data, excluding HEAD and TAIL)
        
    Returns:
        2 ASCII characters representing the last byte in hex (e.g., b'42' for 0x42)
    """
    # Sum all bytes and take last byte only
    checksum = sum(data_bytes) & 0xFF  # Keep only last byte (LSB)
    
    # Convert to 2-character ASCII hex string (e.g., "42" for 0x42)
    checksum_hex = f"{checksum:02X}"
    
    # Return as bytes
    return checksum_hex.encode('ascii')
```

### Message Construction Example

```python
def build_set_command(command_byte, data_value):
    """
    Build a SET command frame.
    
    Args:
        command_byte: Single byte command (e.g., b'M', b'C')
        data_value: Numeric value or string to send
        
    Returns:
        Complete command frame as bytes
    """
    HEAD = b'<'
    TAIL = b'>'
    SEPARATOR = b'='
    
    # Convert data to ASCII representation
    if isinstance(data_value, int):
        data_ascii = str(data_value).encode('ascii')
    else:
        data_ascii = data_value.encode('ascii')
    
    # Build message without checksum
    message_body = command_byte + SEPARATOR + data_ascii
    
    # Calculate checksum
    checksum = calculate_checksum(message_body)
    
    # Assemble complete frame
    frame = HEAD + message_body + checksum + TAIL
    
    return frame
```

### Response Parsing Example

```python
def parse_response(response_bytes):
    """
    Parse response frame and validate.
    
    Args:
        response_bytes: Complete response frame
        
    Returns:
        dict with 'command' and 'data' keys
        
    Raises:
        ValueError: Invalid frame format or checksum
    """
    if len(response_bytes) < 6:
        raise ValueError("Response too short")
    
    # Validate frame markers
    if response_bytes[0:1] != b'[' or response_bytes[-1:] != b']':
        raise ValueError("Invalid frame markers")
    
    # Extract components
    command = response_bytes[1:2]
    
    # Find separator if present
    if b'=' in response_bytes:
        sep_idx = response_bytes.index(b'=')
        data_and_checksum = response_bytes[sep_idx+1:-1]
        
        # Last 2 bytes before TAIL are checksum (2 ASCII hex characters)
        data = data_and_checksum[:-2]
        received_checksum = data_and_checksum[-2:]
        
        # Calculate expected checksum (Command + Separator + Data)
        message_body = response_bytes[1:-3]  # Everything except HEAD, checksum, TAIL
        expected_checksum = calculate_checksum(message_body)
        
        if received_checksum != expected_checksum:
            raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {received_checksum}")
        
        return {
            'command': command.decode('ascii'),
            'data': data.decode('ascii')
        }
    else:
        # Read response without data (shouldn't happen normally)
        checksum = response_bytes[-3:-1]  # Last 2 bytes before TAIL
        message_body = response_bytes[1:-3]  # Command byte only
        expected_checksum = calculate_checksum(message_body)
        
        if checksum != expected_checksum:
            raise ValueError("Checksum mismatch")
        
        return {
            'command': command.decode('ascii'),
            'data': None
        }
```

## Testing Guidelines

1. **Unit Tests**:
   - Test checksum calculation with known examples
   - Test message construction for each command type
   - Test response parsing with valid and invalid frames

2. **Integration Tests**:
   - Test with actual device if available
   - Use serial port loopback for testing
   - Mock serial port for automated testing

3. **Validation Tests**:
   - Verify all example frames from protocol document
   - Test edge cases (max channel, max ID, etc.)
   - Test error conditions (timeout, bad checksum)

## Usage Example

```python
# Initialize and configure device
with RFSensorProtocol('COM3', timeout=1.0) as sensor:
    # Set communication to 5G
    sensor.set_communication_medium(2)
    
    # Set channel to 128
    sensor.set_channel(128)
    
    # Set device ID
    sensor.set_device_id("000120")
    
    # Set port
    sensor.set_port(2)
    
    # Check RF status
    if sensor.read_rf_status():
        print("RF configuration successful")
    else:
        print("RF configuration failed")
    
    # Read current medium
    medium = sensor.get_communication_medium()
    print(f"Current medium: {medium}")
```

## Key Implementation Notes

1. **ASCII Encoding**: Remember that ALL data in the protocol is ASCII-encoded. A numeric value `2` is transmitted as ASCII character '2' (0x32), not as binary 0x02.

2. **Checksum Scope**: The checksum is calculated from: Command byte + Separator (if present) + Setting Data (if present). Take only the last byte (LSB) of the sum and convert to 2 ASCII hex characters.

3. **Response Validation**: Always validate:
   - Frame markers (HEAD/TAIL)
   - Checksum matches
   - Command byte matches request
   - Data format is as expected

4. **Timeout Handling**: Device may not respond if busy or misconfigured. Implement reasonable timeouts (1-2 seconds recommended).

5. **Read vs Set Commands**: Read commands omit the separator and data fields, containing only HEAD + COMMAND + CHECKSUM + TAIL.

## Error Scenarios to Handle

1. **No Response**: Device not connected or powered off
2. **Partial Response**: Communication interrupted
3. **Invalid Checksum**: Data corruption or protocol mismatch
4. **Unexpected Data**: Device returned error or different format
5. **Serial Port Errors**: Port busy, permission denied, etc.

## Success Criteria

Your implementation should:
- ✓ Correctly construct all command types with valid checksums
- ✓ Parse and validate all response types
- ✓ Handle errors gracefully with meaningful exceptions
- ✓ Provide clean, documented API for all operations
- ✓ Pass validation tests using protocol examples
- ✓ Be compatible with pyserial library
- ✓ Support context manager for resource management
