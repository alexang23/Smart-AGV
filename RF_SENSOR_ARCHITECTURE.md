# RF Sensor Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Application                         │
│                                                                 │
│  • Configure sensor (medium, channel, ID, port)                │
│  • Read sensor status                                          │
│  • Monitor statistics                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Sync/Async API
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RFSensorProtocol                            │
│                                                                 │
│  High-Level API:                                               │
│  ├── set_communication_medium() / _async()                     │
│  ├── get_communication_medium() / _async()                     │
│  ├── set_channel() / _async()                                  │
│  ├── get_channel() / _async()                                  │
│  ├── set_device_id() / _async()                                │
│  ├── get_device_id() / _async()                                │
│  ├── set_port() / _async()                                     │
│  ├── get_port() / _async()                                     │
│  └── read_rf_status() / _async()                               │
│                                                                 │
│  Frame Construction:                                            │
│  ├── build_set_command(cmd, data) → <CMD=DATA_CS>             │
│  └── build_read_command(cmd) → <CMD_CS>                       │
│                                                                 │
│  Frame Parsing:                                                │
│  ├── parse_response(frame) → {command, data}                  │
│  ├── validate_checksum()                                       │
│  └── rf_response_parser() → (command_id, frame)               │
│                                                                 │
│  Error Handling:                                               │
│  ├── ChecksumError (data corruption)                          │
│  ├── FrameError (invalid format)                              │
│  └── ValueError (invalid parameters)                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ send_command_async()
                 │ Custom response_parser
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AsyncSerialPort                             │
│                                                                 │
│  Core Features:                                                │
│  ├── Command-Response Matching                                │
│  │   └── Matches responses using command_id                   │
│  ├── FRAME Mode Protocol                                       │
│  │   ├── Frame detection: '[' header                          │
│  │   ├── Variable-length frame support                        │
│  │   └── Buffer management                                    │
│  ├── Automatic Reconnection                                   │
│  │   ├── Connection state monitoring                          │
│  │   └── Configurable retry logic                             │
│  ├── Response Time Tracking                                   │
│  │   ├── Min/Max/Average times                                │
│  │   └── Histogram distribution                               │
│  └── Statistics & Monitoring                                  │
│      ├── Bytes sent/received                                  │
│      ├── Command/response counts                              │
│      └── Timeout tracking                                     │
│                                                                 │
│  Background Tasks:                                             │
│  ├── _response_reader_loop() - Reads and dispatches responses │
│  ├── _timeout_checker_loop() - Monitors command timeouts      │
│  └── _auto_reconnect_loop() - Handles reconnection            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ pyserial / pyserial-asyncio
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Serial Port                                │
│                                                                 │
│  Configuration:                                                │
│  • Baudrate: 38400                                             │
│  • Data bits: 8                                                │
│  • Parity: None                                                │
│  • Stop bits: 1                                                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ USB/Serial Cable
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RF Sensor Device                          │
│                                                                 │
│  • Receives: <CMD=DATA_CS> or <CMD_CS>                        │
│  • Responds: [CMD=DATA_CS]                                     │
│  • Status codes: 9F (OK), 0F (Fail)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### Write Command Flow (Set Channel Example)

```
User Code
   │
   │ sensor.set_channel(128)
   ▼
RFSensorProtocol
   │
   ├─► Validate input (0-255) ──────────────► ValueError if invalid
   │
   ├─► build_set_command(b'C', 128)
   │   └─► Returns: b'<C=1281B>'
   │       • Command: 'C' (0x43)
   │       • Separator: '=' (0x3D)
   │       • Data: '128' (0x31 0x32 0x38)
   │       • Checksum: '1B' (sum & 0xFF = 0x1B)
   │
   ├─► Generate command_id: "RF_C"
   │
   ├─► send_command_async("RF_C", b'<C=1281B>')
   │
   ▼
AsyncSerialPort
   │
   ├─► Store pending command in dict:
   │   pending_commands["RF_C"] = PendingCommand(...)
   │
   ├─► Write to serial port: b'<C=1281B>'
   │
   ├─► Wait for response (with timeout)...
   │
   │   [Background: _response_reader_loop()]
   │   ├─► Read from serial: b'[C=1281B]'
   │   ├─► Call rf_response_parser(b'[C=1281B]')
   │   │   ├─► parse_response() → {'command': 'C', 'data': '128'}
   │   │   └─► Returns: ("RF_C", b'[C=1281B]')
   │   └─► Dispatch to pending_commands["RF_C"]
   │
   ├─► Receive response: b'[C=1281B]'
   │
   ├─► Calculate response time
   │
   └─► Return to RFSensorProtocol
   │
   ▼
RFSensorProtocol
   │
   ├─► parse_response(b'[C=1281B]')
   │   ├─► Validate frame markers: '[' and ']' ✓
   │   ├─► Extract command: 'C' ✓
   │   ├─► Extract data: '128'
   │   ├─► Extract checksum: '1B'
   │   └─► Validate checksum ✓
   │
   ├─► Verify command matches: 'C' == 'C' ✓
   │
   ├─► Check if data matches: '128' == '128' ✓
   │
   └─► Return True (confirmed)
   │
   ▼
User Code
   │
   └─► if result: print("Channel set!")
```

### Read Command Flow (Get Channel Example)

```
User Code
   │
   │ channel = sensor.get_channel()
   ▼
RFSensorProtocol
   │
   ├─► build_read_command(b'C')
   │   └─► Returns: b'<C43>'
   │       • Command: 'C' (0x43)
   │       • Checksum: '43' (0x43)
   │
   ├─► send_command_async("RF_C", b'<C43>')
   │
   ▼
AsyncSerialPort
   │
   ├─► Write: b'<C43>'
   │
   ├─► Wait for response...
   │
   └─► Receive: b'[C=1281B]'
   │
   ▼
RFSensorProtocol
   │
   ├─► parse_response(b'[C=1281B]')
   │   └─► Returns: {'command': 'C', 'data': '128'}
   │
   ├─► Convert to int: int('128') = 128
   │
   └─► Return 128
   │
   ▼
User Code
   │
   └─► print(f"Channel: {channel}")  # Channel: 128
```

## Error Handling Flow

```
User Code
   │
   │ try:
   │     sensor.set_channel(999)
   ▼
RFSensorProtocol
   │
   ├─► Validate: 999 not in 0-255
   │
   └─► raise ValueError("Invalid channel: 999")
   │
   ▼
User Code
   │
   │ except ValueError as e:
   │     print(f"Invalid input: {e}")


User Code
   │
   │ try:
   │     sensor.set_channel(128)
   ▼
RFSensorProtocol
   │
   └─► send_command_async(...)
   │
   ▼
AsyncSerialPort
   │
   ├─► Write: b'<C=1281B>'
   │
   ├─► Wait for response (timeout=2.0s)...
   │
   ├─► ... 2.0 seconds pass ...
   │
   └─► raise TimeoutError("Command RF_C timeout")
   │
   ▼
User Code
   │
   │ except TimeoutError:
   │     print("Device not responding")


User Code
   │
   │ try:
   │     sensor.set_channel(128)
   ▼
RFSensorProtocol → AsyncSerialPort
   │
   ├─► Receive: b'[C=128XX]'  (corrupted checksum)
   │
   ▼
RFSensorProtocol
   │
   ├─► parse_response(b'[C=128XX]')
   │   ├─► Calculate checksum: '1B'
   │   ├─► Compare: '1B' != 'XX'
   │   └─► raise ChecksumError("Checksum mismatch")
   │
   ▼
User Code
   │
   │ except ChecksumError:
   │     print("Data corruption - retry")
```

## State Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                   RFSensorProtocol States                    │
│                                                              │
│  ┌────────────┐  connect()   ┌────────────┐                │
│  │ Created    │──────────────►│ Connected  │                │
│  │            │               │            │                │
│  └────────────┘               └────┬───────┘                │
│       ▲                            │                        │
│       │                            │ send_command()         │
│       │                            ▼                        │
│       │                       ┌────────────┐               │
│       │                       │  Waiting   │               │
│       │                       │  Response  │               │
│       │                       └────┬───────┘               │
│       │                            │                        │
│       │          Response          │  Timeout              │
│       │          Received          │  Error                │
│       │            ┌───────────────┼─────────┐             │
│       │            ▼               ▼         ▼             │
│       │       ┌────────┐     ┌─────────┐ ┌────────┐       │
│       │       │Success │     │ Timeout │ │ Error  │       │
│       │       │        │     │         │ │        │       │
│       │       └────┬───┘     └────┬────┘ └───┬────┘       │
│       │            │              │          │             │
│       │            └──────────────┴──────────┘             │
│       │                      │                             │
│       │                      ▼                             │
│       │               ┌─────────────┐                      │
│       └───────────────│ disconnect()│                      │
│                       └─────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                                                              │
│           AsyncSerialPort Connection States                  │
│                                                              │
│  ┌──────────────┐                                           │
│  │ DISCONNECTED │◄─────────┐                                │
│  └──────┬───────┘          │                                │
│         │                  │                                │
│         │ connect()        │ disconnect()                   │
│         ▼                  │                                │
│  ┌──────────────┐          │                                │
│  │  CONNECTING  │          │                                │
│  └──────┬───────┘          │                                │
│         │                  │                                │
│         │ Success          │                                │
│         ▼                  │                                │
│  ┌──────────────┐          │                                │
│  │  CONNECTED   │──────────┘                                │
│  └──────┬───────┘                                           │
│         │                                                    │
│         │ Connection Lost                                   │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │ RECONNECTING │                                           │
│  └──────┬───────┘                                           │
│         │                                                    │
│         └─────► (retry loop) ─────┐                         │
│                                    │                         │
│         Success ◄──────────────────┘                         │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │  CONNECTED   │                                           │
│  └──────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Interaction Sequence

```
User          RFSensor      AsyncSerial    Serial Port    Device
 │                │              │              │            │
 │─connect()─────►│              │              │            │
 │                │─connect()───►│              │            │
 │                │              │─open()──────►│            │
 │                │              │              │            │
 │                │◄─Connected───│              │            │
 │◄─Connected─────│              │              │            │
 │                │              │              │            │
 │─set_channel()─►│              │              │            │
 │     (128)      │              │              │            │
 │                │              │              │            │
 │                │─build_cmd()─►│              │            │
 │                │ <C=1281B>    │              │            │
 │                │              │              │            │
 │                │─send_cmd()──►│              │            │
 │                │ "RF_C"       │              │            │
 │                │              │              │            │
 │                │              │─write()─────►│            │
 │                │              │ <C=1281B>    │───────────►│
 │                │              │              │            │
 │                │              │  [Background Reader]       │
 │                │              │              │            │
 │                │              │              │◄───────────│
 │                │              │◄─read()──────│ [C=1281B] │
 │                │              │ [C=1281B]    │            │
 │                │              │              │            │
 │                │              │─parse()─────►│            │
 │                │              │ "RF_C"       │            │
 │                │              │              │            │
 │                │◄─response────│              │            │
 │                │ [C=1281B]    │              │            │
 │                │              │              │            │
 │                │─verify()────►│              │            │
 │                │ checksum ✓   │              │            │
 │                │              │              │            │
 │◄─True──────────│              │              │            │
 │ (confirmed)    │              │              │            │
 │                │              │              │            │
```

## Module Dependencies

```
┌────────────────────────────────────────────────┐
│              RF_sensor.py                      │
│                                                │
│  Classes:                                      │
│  • RFSensorProtocol                           │
│  • CommunicationMedium (Enum)                 │
│  • RFCommand (Enum)                           │
│  • ChecksumError                              │
│  • FrameError                                 │
│                                                │
│  Functions:                                    │
│  • calculate_checksum()                       │
│  • validate_checksum()                        │
│                                                │
│  Tests:                                        │
│  • test_checksum_calculation()                │
│  • test_frame_construction()                  │
│  • test_frame_parsing()                       │
│  • test_invalid_frames()                      │
└──────────────┬─────────────────────────────────┘
               │
               │ imports
               ▼
┌────────────────────────────────────────────────┐
│           serial_gyro.py                       │
│                                                │
│  Classes:                                      │
│  • AsyncSerialPort                            │
│  • ProtocolMode (Enum)                        │
│  • ConnectionState (Enum)                     │
│  • PendingCommand                             │
│                                                │
│  Features:                                     │
│  • Command-response matching                  │
│  • Auto-reconnection                          │
│  • Response time tracking                     │
│  • Statistics monitoring                      │
│  • FRAME/LINE mode support                    │
└──────────────┬─────────────────────────────────┘
               │
               │ imports
               ▼
┌────────────────────────────────────────────────┐
│       pyserial / pyserial-asyncio              │
│                                                │
│  Modules:                                      │
│  • serial                                     │
│  • serial_asyncio                             │
│                                                │
│  Classes:                                      │
│  • Serial                                     │
│  • StreamReader                               │
│  • StreamWriter                               │
└────────────────────────────────────────────────┘
```

## Key Design Patterns

### 1. Strategy Pattern (Protocol Modes)
```
ProtocolMode
├── LINE mode → readline() → parse by line
└── FRAME mode → read_frame() → parse by frame header/length
```

### 2. Observer Pattern (Callbacks)
```
AsyncSerialPort Events
├── on_connected() → User callback
├── on_disconnected() → User callback
└── on_reconnecting() → User callback
```

### 3. Command Pattern (Command-Response Matching)
```
Command Object
├── command_id: "RF_C"
├── data: b'<C=1281B>'
├── timestamp: 1234567890.123
├── timeout: 2.0
└── future: asyncio.Future() → resolves with response
```

### 4. Adapter Pattern (Sync/Async API)
```
Sync API (blocking)
    ↓
Event Loop (asyncio)
    ↓
Async API (coroutines)
```

### 5. Factory Pattern (Frame Construction)
```
Command Type
├── SET → build_set_command(cmd, data)
└── READ → build_read_command(cmd)
```
