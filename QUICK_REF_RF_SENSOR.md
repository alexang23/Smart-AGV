# RF Sensor Quick Reference

## Installation

```bash
pip install pyserial pyserial-asyncio
```

## Quick Start

### Synchronous Usage
```python
from RF_sensor import RFSensorProtocol, CommunicationMedium

# Connect and configure
with RFSensorProtocol('COM3') as sensor:
    # Set medium to 5G
    sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
    
    # Set channel
    sensor.set_channel(128)
    
    # Set device ID
    sensor.set_device_id("000120")
    
    # Set port
    sensor.set_port(2)
    
    # Check RF status
    if sensor.read_rf_status():
        print("Configuration successful!")
    
    # Read current settings
    medium = sensor.get_communication_medium()
    channel = sensor.get_channel()
    print(f"Medium: {medium.name}, Channel: {channel}")
```

### Asynchronous Usage
```python
import asyncio
from RF_sensor import RFSensorProtocol, CommunicationMedium

async def main():
    async with RFSensorProtocol('COM3') as sensor:
        await sensor.set_communication_medium_async(CommunicationMedium.WIFI_5G)
        await sensor.set_channel_async(128)
        
        status = await sensor.read_rf_status_async()
        print(f"RF Status: {'OK' if status else 'FAILED'}")

asyncio.run(main())
```

## API Reference

### Communication Medium

```python
# Communication medium types
CommunicationMedium.IR          # 0 = IR
CommunicationMedium.WIFI_2_4G   # 1 = 2.4GHz WiFi
CommunicationMedium.WIFI_5G     # 2 = 5GHz WiFi

# Set medium (returns bool - confirmed by device)
sensor.set_communication_medium(CommunicationMedium.WIFI_5G)

# Get medium (returns CommunicationMedium enum or None)
medium = sensor.get_communication_medium()
```

### Channel

```python
# Set channel 0-255 (returns bool - confirmed)
sensor.set_channel(128)

# Get channel (returns int or None)
channel = sensor.get_channel()
```

### Device ID

```python
# Set 6-digit ID (string or int, returns bool - confirmed)
sensor.set_device_id("000120")
sensor.set_device_id(120)  # Auto-padded to "000120"

# Get device ID (returns string with possible serial prefix)
device_id = sensor.get_device_id()
# Example: "569A-000120"
```

### Port

```python
# Set port (returns bool - confirmed)
sensor.set_port(2)

# Get port (returns int or None)
port = sensor.get_port()
```

### RF Status

```python
# Check RF configuration (returns bool)
# True = "9F" (RF SET OK)
# False = "0F" (RF SET Fail)
status = sensor.read_rf_status()
```

## Error Handling

```python
from RF_sensor import (
    RFSensorProtocol,
    CommunicationMedium,
    ChecksumError,
    FrameError,
    InvalidCommandError
)

try:
    with RFSensorProtocol('COM3', timeout=2.0) as sensor:
        # Returns True/False for device confirmation
        confirmed = sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
        
        if confirmed:
            print("Device confirmed setting")
        else:
            print("Device did not confirm (but no error)")
            
except ValueError as e:
    # Invalid parameters (programming error)
    print(f"Invalid input: {e}")
    
except ConnectionError as e:
    # Serial port not available or disconnected
    print(f"Connection error: {e}")
    
except TimeoutError as e:
    # Device didn't respond in time
    print(f"Timeout: {e}")
    
except ChecksumError as e:
    # Data corruption detected
    print(f"Checksum error: {e}")
    
except FrameError as e:
    # Invalid frame format
    print(f"Frame error: {e}")
```

## Configuration Options

```python
sensor = RFSensorProtocol(
    port='COM3',                # Serial port
    timeout=2.0,                # Response timeout (seconds)
    auto_reconnect=True,        # Auto-reconnect on disconnect
    debug=False,                # Enable debug logging
)
```

## Statistics & Monitoring

```python
# Get communication statistics
stats = sensor.get_statistics()
print(f"Commands sent: {stats['commands_sent']}")
print(f"Responses received: {stats['responses_received']}")
print(f"Timeouts: {stats['timeouts']}")

# Get response time statistics
rt_stats = sensor.get_response_time_stats()
print(f"Average response time: {rt_stats['avg_ms']:.2f} ms")

# Print formatted statistics
sensor.print_statistics()
```

## Protocol Details

### Frame Format

**Command (Write)**:
```
< + Command + = + Data + Checksum + >
Example: <M=2BC>
```

**Response**:
```
[ + Command + = + Data + Checksum + ]
Example: [M=2BC]
```

**Read Command**:
```
< + Command + Checksum + >
Example: <M4D>
```

### Checksum Calculation

```python
from RF_sensor import calculate_checksum

# Calculate checksum for data
checksum = calculate_checksum(b'M=2')
# Returns: b'BC'

# Algorithm: Sum(bytes) & 0xFF, convert to 2 ASCII hex chars
```

### Manual Frame Construction

```python
from RF_sensor import RFSensorProtocol

# Build SET command frame
frame = RFSensorProtocol.build_set_command(b'M', 2)
# Returns: b'<M=2BC>'

# Build READ command frame
frame = RFSensorProtocol.build_read_command(b'M')
# Returns: b'<M4D>'

# Parse response frame
parsed = RFSensorProtocol.parse_response(b'[M=2BC]')
# Returns: {'command': 'M', 'data': '2', 'raw': b'[M=2BC]'}
```

## Testing

```bash
# Run all unit tests (no device needed)
python RF_sensor.py test

# Run synchronous example (requires device on COM3)
python RF_sensor.py example-sync

# Run asynchronous example (requires device on COM3)
python RF_sensor.py example-async
```

## Command Reference Table

| Command | Byte | Description | Data Range | Example |
|---------|------|-------------|------------|---------|
| Medium  | 'M' (0x4D) | Communication medium | 0=IR, 1=2.4G, 2=5G | `<M=2BC>` |
| Channel | 'C' (0x43) | Communication channel | 0-255 | `<C=1281B>` |
| ID      | 'A' (0x41) | Device ID | 6 digits (000000-999999) | `<A=000120A1>` |
| Port    | 'N' (0x4E) | Port setting | Numeric | `<N=2BD>` |
| Status  | 'Y' (0x59) | RF status (read only) | N/A | `<Y59>` |

## Response Codes

### RF Status Response
- `[Y=9F..]` - RF configuration successful
- `[Y=0F..]` - RF configuration failed

## Common Patterns

### Configure and Verify
```python
with RFSensorProtocol('COM3') as sensor:
    # Configure all settings
    sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
    sensor.set_channel(128)
    sensor.set_device_id("000120")
    sensor.set_port(2)
    
    # Verify with RF status
    if sensor.read_rf_status():
        print("✓ Configuration successful")
    else:
        print("✗ Configuration failed")
```

### Read All Settings
```python
with RFSensorProtocol('COM3') as sensor:
    settings = {
        'medium': sensor.get_communication_medium(),
        'channel': sensor.get_channel(),
        'device_id': sensor.get_device_id(),
        'port': sensor.get_port(),
        'rf_status': sensor.read_rf_status()
    }
    
    print(f"Current Settings: {settings}")
```

### Error Recovery
```python
sensor = RFSensorProtocol('COM3', auto_reconnect=True)
sensor.connect()

try:
    for attempt in range(3):
        try:
            sensor.set_channel(128)
            break  # Success
        except TimeoutError:
            print(f"Timeout on attempt {attempt+1}, retrying...")
            continue
except Exception as e:
    print(f"Failed after 3 attempts: {e}")
finally:
    sensor.disconnect()
```

## Logging

```python
import logging

# Enable debug logging for troubleshooting
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or enable only for RF sensor
logging.getLogger('RFSensor(COM3)').setLevel(logging.DEBUG)
```

## Tips & Best Practices

1. **Use context manager** - Automatically handles connection/disconnection
2. **Check return values** - `set_*()` methods return False if device didn't confirm
3. **Handle timeouts** - Use try/except for TimeoutError
4. **Enable auto_reconnect** - Helps with unstable connections
5. **Monitor statistics** - Use `print_statistics()` for debugging
6. **Test without device** - Run unit tests first
7. **Validate inputs** - Library raises ValueError for invalid parameters

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: serial` | Install: `pip install pyserial pyserial-asyncio` |
| `ConnectionError` | Check COM port name, device power, USB cable |
| `TimeoutError` | Check baud rate (38400), increase timeout value |
| `ChecksumError` | Check for electromagnetic interference, try again |
| `FrameError` | Device may be using different protocol version |
| Device not confirming | Check `read_rf_status()` for details |

## Complete Example

```python
import logging
from RF_sensor import RFSensorProtocol, CommunicationMedium

# Configure logging
logging.basicConfig(level=logging.INFO)

def configure_rf_sensor(port='COM3'):
    """Complete RF sensor configuration example"""
    try:
        with RFSensorProtocol(port, timeout=2.0, auto_reconnect=True) as sensor:
            print(f"✓ Connected to {port}")
            
            # Configure device
            print("\nConfiguring device...")
            sensor.set_communication_medium(CommunicationMedium.WIFI_5G)
            sensor.set_channel(128)
            sensor.set_device_id("000120")
            sensor.set_port(2)
            
            # Verify configuration
            print("\nVerifying configuration...")
            if sensor.read_rf_status():
                print("✓ RF configuration successful!")
            else:
                print("✗ RF configuration failed")
                return False
            
            # Read and display current settings
            print("\nCurrent Settings:")
            medium = sensor.get_communication_medium()
            channel = sensor.get_channel()
            device_id = sensor.get_device_id()
            port_num = sensor.get_port()
            
            print(f"  Medium:    {medium.name if medium else 'Unknown'}")
            print(f"  Channel:   {channel}")
            print(f"  Device ID: {device_id}")
            print(f"  Port:      {port_num}")
            
            # Show statistics
            sensor.print_statistics()
            
            return True
            
    except ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print(f"   Check that device is connected to {port}")
        return False
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
        print("   Device not responding - check power and connections")
        return False
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = configure_rf_sensor('COM3')
    exit(0 if success else 1)
```
