########################################
# sun1 = Sunion('/dev/ttyAMA0')
# sun1.daemon = True
# sun1.start()
########################################

import time
import serial
import string
import binascii
import threading
import traceback
import collections
import sys
import json
from time import sleep
from config import settings
from datetime import datetime
from global_log import Logger
from collections import Counter
from typing import Optional, List, Dict, Any

import queue
import schedule

class UHFProtocolError(Exception):
    """Exception for UHF protocol specific errors"""
    pass

class UHFCommand:
    """UHF Protocol Command Structure"""
    
    # Command frame structure constants
    HEADER = 0xFF
    EXTENDED_CMD_CODE = 0xAA
    MODULETECH_MARKER = b'Moduletech'  # [4D 6F 64 75 6C 65 74 65 63 68]
    HEARTBEAT_MARKER = b'XTSJ'  # [58 54 53 4A]
    TERMINATOR = 0xBB
    
    # Common command codes
    INVENTORY_CMD = 0x22
    READ_DATA_CMD = 0x39
    WRITE_DATA_CMD = 0x49
    START_ASYNCHRONOUS_INVENTORY = 0xAA48
    STOP_ASYNCHRONOUS_INVENTORY = 0xAA49
    INITIALIZE_03 = 0x03
    INITIALIZE_00 = 0x00
    INITIALIZE_04 = 0x04
    INITIALIZE_06 = 0x06
    INITIALIZE_61 = 0x61
    INITIALIZE_96 = 0x96
    INITIALIZE_9A = 0x9A
    INITIALIZE_6A = 0x6A
    INITIALIZE_62 = 0x62
    INITIALIZE_63 = 0x63
    INITIALIZE_6B = 0x6B
    INITIALIZE_61 = 0x61
    INITIALIZE_91 = 0x91
    
    def __init__(self, command_code: int, data: bytes = b'', is_extended: bool = False):
        self.command_code = command_code
        self.data = data
        self.is_extended = is_extended
        
    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """
        CRC-16-CCITT calculation (poly=0x1021, init=0xFFFF), skipping first byte (frame header)
        """
        crc = 0xFFFF
        for b in data[1:]:  # skip frame header
            dcdBitMask = 0x80
            for _ in range(8):
                xorFlag = crc & 0x8000
                crc = (crc << 1) & 0xFFFF
                bit = 1 if (b & dcdBitMask) == dcdBitMask else 0
                crc |= bit
                if xorFlag:
                    crc ^= 0x1021
                dcdBitMask >>= 1
        return crc
    
    def build_standard_command(self) -> bytes:
        """
        Build standard command frame:
        Header(1) + Data Length(1) + Command Code(1) + Data(N) + CRC-16(2)
        """
        if self.is_extended:
            raise UHFProtocolError("Use build_extended_command for extended commands")
            
        header = self.HEADER
        data_length = len(self.data)
        
        # Build command without CRC
        cmd_without_crc = bytes([header, data_length, self.command_code]) + self.data
        
        # Calculate CRC-16 (high byte first - MSB)
        crc = self.calculate_crc16(cmd_without_crc)
        crc_high = (crc >> 8) & 0xFF
        crc_low = crc & 0xFF
        
        return cmd_without_crc + bytes([crc_high, crc_low])
    
    def build_extended_command(self, subcommand_code: int, subcommand_data: bytes = b'') -> bytes:
        """
        Build extended command frame (Command Code 0xAA):
        Header(1) + Data Length(1) + 0xAA + Extended Data + CRC-16(2)
        
        Extended Data structure:
        Subcommand Marker(10) + Subcommand Code(2) + Subcommand Data(N) + SubCRC(1) + Terminator(1)
        """
        # Subcommand Code (2 bytes, big-endian)
        subcmd_bytes = bytes([(subcommand_code >> 8) & 0xFF, subcommand_code & 0xFF])
        
        # Calculate SubCRC: XOR of subcommand code + subcommand data
        subcrc_data = subcmd_bytes + subcommand_data
        subcrc = 0
        for byte in subcrc_data:
            subcrc += byte
        subcrc = subcrc & 0xFF
        
        # Build extended data field
        extended_data = (self.MODULETECH_MARKER + 
                        subcmd_bytes + 
                        subcommand_data + 
                        bytes([subcrc, self.TERMINATOR]))
        
        # Create standard frame with extended data
        header = self.HEADER
        data_length = len(extended_data)
        
        cmd_without_crc = bytes([header, data_length, self.EXTENDED_CMD_CODE]) + extended_data
        
        # Calculate main CRC-16
        crc = self.calculate_crc16(cmd_without_crc)
        crc_high = (crc >> 8) & 0xFF
        crc_low = crc & 0xFF
        
        return cmd_without_crc + bytes([crc_high, crc_low])
    
class UHFResponse:
    """UHF Protocol Response Parser"""
    
    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data
        self.header = None
        self.data_length = None
        self.command_code = None
        self.status_code = None
        self.data = None
        self.crc = None
        self.is_valid = False
        self.metadata = None
        self.parse()
    
    def parse(self):
        """
        Parse response frame:
        Header(1) + Data Length(1) + Command Code(1) + Status Code(2) + Data(N) + CRC-16(2)
        """
        if len(self.raw_data) < 6:
            return
            
        try:
            self.header = self.raw_data[0]
            self.data_length = self.raw_data[1]
            self.command_code = self.raw_data[2]
            self.status_code = (self.raw_data[3] << 8) | self.raw_data[4]  # Big-endian
            
            # Check minimum frame length
            expected_length = 5 + self.data_length + 2  # Header + DataLen + CmdCode + StatusCode + Data + CRC
            if len(self.raw_data) < expected_length:
                return
                
            # Extract data field
            if self.data_length > 0:
                self.data = self.raw_data[5:5+self.data_length]
            else:
                self.data = b''
                
            # Extract CRC
            crc_start = 5 + self.data_length
            if len(self.raw_data) >= crc_start + 2:
                self.crc = (self.raw_data[crc_start] << 8) | self.raw_data[crc_start + 1]
                
            # Validate frame
            if (self.header == UHFCommand.HEADER and 
                self.status_code == 0):  # 0 means success
                self.is_valid = True
                
        except Exception as e:
            print(f"Error parsing response: {e}")
    
    def is_extended_response(self) -> bool:
        """Check if this is an extended command response"""
        return (self.command_code == UHFCommand.EXTENDED_CMD_CODE and 
                self.data and 
                len(self.data) >= 12 and
                self.data[:10] == UHFCommand.MODULETECH_MARKER)
    
    def is_heartbeat_response(self) -> bool:
        """Check if this is a heartbeat response"""
        return (self.command_code == UHFCommand.EXTENDED_CMD_CODE and
                self.data and
                len(self.data) == 6 and
                self.data[:4] == UHFCommand.HEARTBEAT_MARKER[:4])

    def parse_metadata(self, metadata_flags: int = 0, start_offset: int = 2) -> Optional[Dict[str, Any]]:
        """
        Parse metadata from response data according to UHF protocol specification
        
        Args:
            metadata_flags: Metadata flags indicating which metadata fields are present
            start_offset: Starting offset in self.data to begin parsing
            
        Returns:
            Dictionary containing parsed metadata fields and 'data_offset' indicating end position
        """
        if not self.data or start_offset >= len(self.data):
            return None
            
        try:
            metadata = {}
            offset = start_offset
            
            # Parse metadata fields based on flags
            if metadata_flags & 0x0001:  # Read Count
                if offset + 1 <= len(self.data):
                    metadata['read_count'] = self.data[offset]
                    offset += 1
                    
            if metadata_flags & 0x0002:  # RSSI
                if offset + 1 <= len(self.data):
                    rssi_raw = self.data[offset]
                    # Convert from two's complement: subtract 256 from original value if negative
                    metadata['rssi'] = rssi_raw if rssi_raw < 128 else rssi_raw - 256
                    offset += 1
                    
            if metadata_flags & 0x0004:  # Antenna ID
                if offset + 1 <= len(self.data):
                    metadata['antenna_id'] = self.data[offset]
                    offset += 1
                    
            if metadata_flags & 0x0008:  # Frequency
                if offset + 3 <= len(self.data):
                    # Frequency in kHz (3 bytes)
                    freq = (self.data[offset] << 16) | (self.data[offset + 1] << 8) | self.data[offset + 2]
                    metadata['frequency'] = freq
                    offset += 3
                    
            if metadata_flags & 0x0010:  # Timestamp
                if offset + 4 <= len(self.data):
                    # Timestamp in milliseconds (4 bytes, big-endian)
                    timestamp = (self.data[offset] << 24) | (self.data[offset + 1] << 16) | \
                               (self.data[offset + 2] << 8) | self.data[offset + 3]
                    metadata['timestamp'] = timestamp
                    offset += 4
                    
            if metadata_flags & 0x0020:  # Phase Value
                # For asynchronous inventory (0xAA), phase is 2 bytes end phase value
                # Lower 12 bits are valid, calculated as: (phase_value/4096)*360 degrees
                if offset + 2 <= len(self.data):
                    phase_raw = (self.data[offset] << 8) | self.data[offset + 1]
                    phase_value = phase_raw & 0x0FFF  # Lower 12 bits
                    metadata['phase_degrees'] = (phase_value / 4096) * 360
                    metadata['phase_raw'] = phase_raw
                    offset += 2
                    
            if metadata_flags & 0x0040:  # Protocol ID
                if offset + 1 <= len(self.data):
                    metadata['protocol_id'] = self.data[offset]
                    offset += 1
                    
            if metadata_flags & 0x0080:  # Tag Data Length
                if offset + 2 <= len(self.data):
                    # Tag data length in bits (2 bytes)
                    tag_data_length = (self.data[offset] << 8) | self.data[offset + 1]
                    metadata['tag_data_length_bits'] = tag_data_length
                    metadata['tag_data_length_bytes'] = tag_data_length // 8
                    offset += 2
                    
                    # Parse tag data if length > 0
                    if tag_data_length > 0 and offset + metadata['tag_data_length_bytes'] <= len(self.data):
                        tag_data = self.data[offset:offset + metadata['tag_data_length_bytes']]
                        metadata['tag_data'] = tag_data
                        offset += metadata['tag_data_length_bytes']
            
            # Store the offset where metadata ends
            metadata['data_offset'] = offset
            
            return metadata
            
        except Exception as e:
            print(f"Error parsing metadata: {e}")
            return None

    def parse_epc(self) -> Optional[Dict[str, Any]]:
        pass

    def get_extended_data(self) -> Optional[Dict[str, Any]]:
        """Parse extended command response data"""
        if not self.is_extended_response():
            return None
            
        try:
            subcommand_code = (self.data[10] << 8) | self.data[11]
            subcommand_data = self.data[12:-2] if len(self.data) > 13 else b''
            subcrc = self.data[-2] if len(self.data) >= 2 else 0
            terminator = self.data[-1] if len(self.data) >= 1 else 0
            
            return {
                'subcommand_code': subcommand_code,
                'subcommand_data': subcommand_data,
                'subcrc': subcrc,
                'terminator': terminator
            }
        except Exception as e:
            print(f"Error parsing extended data: {e}")
            return None    

class SerialPortHandler:
    """UHF Protocol Serial Communication Handler"""
    
    def __init__(self, port='COM14', baudrate=115200, timeout=0.5, max_queue_size=200):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.ser.reset_input_buffer()
        time.sleep(2)  # Connection stabilization time

        # Communication queues
        self.incoming_queue = queue.Queue(maxsize=max_queue_size)
        self.outgoing_queue = queue.Queue()

        self.running = False

        # Worker threads
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)

    def start(self):
        """Start serial communication threads"""
        if self.running:
            return
        
        if not self.ser.is_open:
            self.ser.open()
            self.ser.reset_input_buffer()
            time.sleep(2)
        self.running = True
        self.reader_thread.start()
        self.writer_thread.start()

    def stop(self):
        """Stop serial communication threads"""
        self.running = False
        if self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1)
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=1)
        if self.ser.is_open:
            self.ser.close()

    def _read_loop(self):
        """Continuous data reading loop"""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    if data:
                        self.incoming_queue.put_nowait(data)
                time.sleep(0.001)  # Small delay to prevent CPU overload
            except queue.Full:
                print("Warning: Incoming queue full. Dropping data.")
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    print(f"Read loop error: {e}")

    def _write_loop(self):
        """Continuous data writing loop"""
        while self.running:
            try:
                data = self.outgoing_queue.get(timeout=0.1)
                if self.ser.is_open:
                    self.ser.write(data)
                    self.ser.flush()  # Ensure data is sent immediately
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"Write loop error: {e}")

    def reset_buffer(self):
        try:
            if self.ser.is_open:
                self.ser.reset_input_buffer()
                time.sleep(0.2)
                # self.ser.reset_output_buffer()
                # time.sleep(0.2)
                return True
            else:
                return False
        except Exception as e:
            print(f"Error reset_buffer command: {e}")
            return False

    def send_direct_command(self, cmd_bytes: bytes = b'') -> bytes:
        try:
            # Clear receive queue
            while not self.incoming_queue.empty():
                try:
                    self.incoming_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Send command
            self.outgoing_queue.put(cmd_bytes)
            return True

        except Exception as e:
            print(f"Error sending direct command: {e}")
            return None

    def send_command(self, command: UHFCommand, timeout: float = 5.0) -> Optional[UHFResponse]:
        """
        Send UHF command and wait for response
        Following UHF protocol: timeout = 5s + command execution time
        """
        try:
            # Build command frame
            if command.is_extended:
                # cmd_bytes = command.build_extended_command(0x4800, command.data)  # Default subcommand
                cmd_bytes = command.build_extended_command(command.command_code, command.data)  # Default subcommand
            else:
                cmd_bytes = command.build_standard_command()
            
            if settings.UHF_RFID_DEBUG_ENABLE:
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} TX: {[f"{b:02X}" for b in cmd_bytes]}')
            
            # Clear receive queue
            while not self.incoming_queue.empty():
                try:
                    self.incoming_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Send command
            self.outgoing_queue.put(cmd_bytes)
            
            # Wait for response with protocol-specified timeout
            start_time = time.time()
            received_data = b''
            
            while (time.time() - start_time) < timeout:
                try:
                    data = self.incoming_queue.get(timeout=0.1)
                    received_data += data
                    
                    # Try to parse complete frame
                    if len(received_data) >= 6:  # Minimum frame size
                        try:
                            response = UHFResponse(received_data)
                            if response.is_valid:
                                if settings.UHF_RFID_DEBUG_ENABLE:
                                    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} RX: {[f"{b:02X}" for b in received_data]}')
                                return response
                        except Exception:
                            # Continue collecting data if parse fails
                            pass
                            
                except queue.Empty:
                    continue
            
            # Timeout occurred
            if received_data:
                print(f'Partial response received: {[f"{b:02X}" for b in received_data]}')
            raise TimeoutError(f'Timeout waiting for response to command 0x{command.command_code:02X}')
            
        except Exception as e:
            print(f"Error sending command: {e}")
            return None

    def receive_command(self, timeout: float = 5.0) -> Optional[UHFResponse]:
        """
        Receive UHF command response
        Following UHF protocol: timeout = 5s + command execution time
        """
        try:
            # Wait for response with protocol-specified timeout
            start_time = time.time()
            received_data = b''

            while (time.time() - start_time) < timeout:
                try:
                    data = self.incoming_queue.get(timeout=0.1)
                    received_data += data

                    # Try to parse complete frame
                    if len(received_data) >= 6:  # Minimum frame size
                        try:
                            response = UHFResponse(received_data)
                            if response.is_valid:
                                if settings.UHF_RFID_DEBUG_ENABLE:
                                    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} RX: {[f"{b:02X}" for b in received_data]}')
                                return response
                        except Exception:
                            # Continue collecting data if parse fails
                            pass

                except queue.Empty:
                    continue

            # Timeout occurred
            if received_data:
                print(f'Partial response received: {[f"{b:02X}" for b in received_data]}')
            raise TimeoutError(f'Timeout waiting for response')

        except Exception as e:
            print(f"Error receiving command: {e}")
            return None

class SunionUHF_SL(threading.Thread):
    def __init__(self, devPath, type='UHF_SL', controller=None, event_mgr=None, trycount=10, pickcount=3, timeout=500):
        threading.Thread.__init__(self)
        self.stop = False
        self.trycount = trycount
        self.pickcount = pickcount
        self.sensors = [False]*4
        self.rfids = ['']*4
        self.prev_rfids = ['']*4
        self.lastTime = [time.monotonic_ns()]*4
        self.count = [0]*4
        self.tmp_rfids = [['']*trycount, ['']*trycount, ['']*trycount, ['']*trycount]
        # self.tmp_rfids = [[] for _ in range(trycount)]
        self.access_mode = [0]*4
        self.controller = controller
        self.event_mgr = event_mgr
        self.devPath = devPath
        self.type = type
        self.rfid_name = f"rfid_{type}"
        self.page_num = 1 # rfid_config['read_page_nums']
        self.dev_rs485 = None
        self.logger = Logger("rfid_UHF", "rfid_UHF.log")
        self.receive_queue = collections.deque()
        self.svr_enable = True
        self.is_initialized = False
        
        try:
            self.dev_rs485 = SerialPortHandler(self.devPath)
            self.dev_rs485.start()
            time.sleep(0.5)
            if not self.initialize_reader():
                self.logger.error("Failed to initialize UHF reader")
                self.dev_rs485.stop()
                self.dev_rs485 = None
        except Exception as err:
            self.logger.error(str(err))
            self.dev_rs485 = None



    def get_most_common_rfid(self, rfid_list, rfid_length=settings.UHF_RFID_LENGTH):
        # [b'000008M10013', b'000008M10013', b'000008M10013', None, None, None, b'000008M10013', b'000008M10013', b'000008M10013', None]

        # Filter strings with length 12
        # filtered = [s for s in rfid_list if len(s) == 12] can not use for None

        filtered = []
        for item in rfid_list:
            if item is None or not item:
                continue
            # if isinstance(item, bytes):
            #     item = item.decode('utf-8', errors='ignore')
            if len(item) >= rfid_length:
                filtered.append(item)

        # Count occurrences
        counts = Counter(filtered)

        # Filter items with at least 3 occurrences
        valid = {s: count for s, count in counts.items() if count >= self.pickcount}

        # Return the one with the highest count if it exists
        if valid:
            return max(valid, key=valid.get)
        # return None
        return '--------'

    def clear_rfid(self, port_no=1):
        self.prev_rfids[port_no-1] = self.rfids[port_no-1]
        self.rfids[port_no-1] = ''
        self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text='remove rfid', server=True)
        # self.logger.info(f"prev_carrier_id={self.prev_rfids[port_no-1]}, carrier_id={self.rfids[port_no-1]}")
        self.logger.info(f"{self.rfid_name} port_no {port_no} : remove rfid [{self.prev_rfids[port_no-1]}]")

    def cmd_read(self, port_no=1, rfid_length=settings.UHF_RFID_LENGTH, rfid_order=settings.UHF_RFID_ORDER):
        try:
            self.logger.info(f"{self.rfid_name} port_no {port_no} start cmd_read")

            if self.start_tag_reading(port_no):
                i = 0
                while i < self.trycount:
                    response = self.dev_rs485.receive_command(timeout=10.0)
                    
                    if response and response.is_valid:
                        if response.is_heartbeat_response():
                            self.logger.info(f"{self.rfid_name} port_no {port_no} Received heartbeat response, ignoring...")
                            continue
                        metadata_flag = response.data[0] << 8 | response.data[1]
                        tag = self._parse_inventory_response(response, metadata_flag)
                        if tag:
                            metadata = tag.get('metadata', {})
                            if settings.UHF_RFID_DEBUG_ENABLE:
                                print(f"EPC: {tag.get('epc', '')}, EPC Bytes: {tag.get('epc_bytes', b'').hex().upper()}, RSSI: {metadata.get('rssi', 0)}, Antenna ID: {metadata.get('antenna_id', 0)}, Timestamp: {metadata.get('timestamp', 0)}, PC Word: {tag.get('pc_word', 0):04X}, Tag CRC: {tag.get('tag_crc', 0):04X}")
                        rfid = tag.get('epc_bytes', '') if tag else ''
                        # rfid = response.data[11:-2]
                        # rfid = bytearray(response.data)[11:-2].decode('utf-8', errors='replace')
                        # rfid = ''.join(list(response.data)[11:-2])
                        # print(f'rfid={[f"{b:02X}" for b in rfid]}')
                        # print(f"Read tag successfully rfid={rfid.hex().upper()}")
                        # print(f"Read tag rfid={rfid}")
                        self.tmp_rfids[port_no-1][i] = rfid
                    else:
                        self.logger.error(f"{self.rfid_name} port_no {port_no} Failed to read tag")
                        self.tmp_rfids[port_no-1][i] = ''
                    i += 1

                if self.stop_tag_reading():
                    # self.logger.info(f"{self.rfid_name} Stopped tag reading")
                    pass
                else:
                    self.logger.error(f"{self.rfid_name} port_no {port_no} Failed to stop tag reading")
            else:
                self.logger.error(f"{self.rfid_name} port_no {port_no} Failed to start tag reading")

            self.logger.info(f"{self.rfid_name} port_no {port_no} : rfids = {self.tmp_rfids[port_no-1]}")

            rfid_value = self.get_most_common_rfid(self.tmp_rfids[port_no-1], rfid_length)
            print(f"rfid_value : {rfid_value}")
            self.prev_rfids[port_no-1] = self.rfids[port_no-1]
            if rfid_value:
                # rfid_orig = rfid_value.decode('ascii', errors='replace')
                # rfid_orig = ''.join(chr(x) if chr(x).isprintable() else '?' for x in rfid_value)
                rfid_orig = ''.join(chr(x) if (32 <= x and x < 127) else '?' for x in rfid_value)
                print(f"rfid_orig : {rfid_orig}")
                rfidtmp = rfid_orig[:rfid_length]
                # for x in rfidtmp:
                #     if not x.isprintable():
                #         print(f"Non-printable character found in RFID: {x} (ord: {ord(x)})")
                #     else:
                #         print(f"Printable character in RFID: {x}, {ord(x):02X}")
                # rfid = ''.join(x if x.isprintable() else '?' for x in rfidtmp)
                rfid = rfidtmp
                print(f"rfid : {rfid}")
                rfid = ''.join(reversed(rfid)) if rfid_order else ''.join(rfid)
                # print(f"rfid : {rfid}")
                self.rfids[port_no-1] = rfid
            else:
                self.rfids[port_no-1] = ''

            # if rfid_orig:
            #     # rfid = rfid_orig[:settings.LF_RFID_LENGTH]
            #     rfid = rfid_orig[:rfid_length]
            #     rfid = ''.join(reversed(rfid)) if rfid_order else ''.join(rfid)
            # else:
            #     rfid = rfid_orig

            if self.prev_rfids[port_no-1] != self.rfids[port_no-1]:
                if self.rfids[port_no-1]:
                    self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=1, msg_text='place rfid', server=True)
                else:
                    self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text='remove rfid', server=True)
            
            try:
                # print(f"UHF RFID value={self.rfids[port_no-1]}, prev value={self.prev_rfids[port_no-1]}")
                self.logger.info(f"{self.rfid_name} port_no {port_no} prev_carrier_id={self.prev_rfids[port_no-1]}, carrier_id={self.rfids[port_no-1]}")
            except Exception as err:
                self.logger.error(str(err))

            # self.write_sunion(port_id)
            # res = self.read_sunion()
            # if type(res) == str:
            #     return res[::-1]
            # else:
            #     return res
        except Exception as err:
            print(str(err))

    def cmd_write(self, rfid_id, port_id = 1, page_num = 1):
        pass
        # cmd = 'K1'
        # header = 'S0%d%s'%(rfid_config['dev ID'], cmd)
        # data = '%02XM%02d%08s'%(port_id, page_num, rfid_id)
        # self.write_sunion(header, data)
        # return self.read_sunion()

    ####################

    def mqtt_publish_status(self, port_no, type=2, code=0, subcode=-1, msg_text='rfid UHF init'):
        data = {}
        
        data['Server'] = True

        data['device_id'] = settings.DEVICE_ID
        data['port_id'] = str(port_no)
        data['port_no'] = port_no
        data['dual_port'] = 0
        if settings.RFID_DEVICE_ONLY:
            data['mode'] = 2 # Access Mode 0: Unknown, 1: Auto, 2: Manual
        else:
            data['mode'] = self.access_mode[port_no-1]
        data['eqp_state'] = self.controller.equipment_state
        data['prev_carrier_id'] = self.prev_rfids[port_no-1]
        data['carrier_id'] = self.rfids[port_no-1]
        data['type'] = type
        data['stream'] = -1
        data['function'] = -1
        data['code_id'] = code
        data['sub_id'] = subcode
        data['msg_text'] = msg_text
        data['status'] = ''
        data['occurred_at'] = time.time()
        self.event_mgr.on_notify(data)

    def mqtt_publish(self, port_no, prev_rfid_data, rfid_data, type, code, subcode=-1, msg_text=None, server=False):
        data = {}
        
        if server:
            data['Server'] = True

        data['device_id'] = settings.DEVICE_ID
        data['port_id'] = str(port_no)
        data['port_no'] = port_no
        data['dual_port'] = 0
        data['mode'] = self.access_mode[port_no-1]
        data['eqp_state'] = self.controller.equipment_state
        data['prev_carrier_id'] = prev_rfid_data
        data['carrier_id'] = rfid_data
        data['type'] = type
        data['stream'] = -1
        data['function'] = -1
        data['code_id'] = code
        data['sub_id'] = subcode
        data['msg_text'] = msg_text
        data['status'] = ''
        data['occurred_at'] = time.time()
        self.event_mgr.on_notify(data)

    def data_process(self, data):
        pass

    def run(self):
        # schedule.every(30).seconds.do(self.cmd_read)
        self.logger.info(f"RFID UHF Starting")
        while not self.stop:
            if self.dev_rs485 == None:
                try:
                    self.dev_rs485 = SerialPortHandler(self.devPath)
                    self.dev_rs485.start()
                    time.sleep(0.5)
                    if not self.initialize_reader():
                        self.logger.error("Failed to initialize UHF reader")
                        self.dev_rs485.stop()
                        self.dev_rs485 = None
                except Exception as err:
                    self.logger.error(str(err))
                    self.dev_rs485 = None
                    time.sleep(5)
            while self.receive_queue :
                data = self.receive_queue.popleft()
                # self.logger.debug('inside webapi_svr run = {}'.format(data))
                # print('inside mqtt_svr run = {}'.format(data))
                if self.svr_enable :
                    self.data_process(data)
                    # if 'device_id' in data:
                    #     del data['device_id']
            sleep(10)

    def start(self):
        """Initialize serial communication"""
        self.dev_rs485.start()
        
    def stop(self):
        """Stop serial communication"""
        self.dev_rs485.stop()
        
    def initialize_reader(self) -> bool:
        """
        Initialize RFID reader according to UHF protocol
        Performs basic setup and configuration
        """
        self.logger.info(f"{self.rfid_name} === Initializing UHF RFID Reader ===")
        
        try:
            # Step 1: Get reader information
            if not self._stop_asynchronous_inventory():
                self.logger.error(f"{self.rfid_name} Failed to write _stop_asynchronous_inventory")
                return False
                
            if not self._unknown_command():
                self.logger.error(f"{self.rfid_name} Failed to write _unknown_command")
                return False
            
            if not self._initial_03():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_03")
                return False
            
            if not self._unknown_command_00():
                self.logger.error(f"{self.rfid_name} Failed to write _unknown_command_00")
                return False
            
            if not self._reset_serial_buffer():
                self.logger.error(f"{self.rfid_name} Failed to write _reset_serial_buffer")
                return False
            
            if not self._initial_03():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_03")
                return False
            
            if not self._initial_03():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_03")
                return False

            if not self._initial_04():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_04")
                return False
            
            # Data: FF 04 06 00 01 C2 00 A4 60
            if not self._initial_06():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_06")
                return False
            
            # Data: FF 01 61 05 BD B8
            if not self._initial_61():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_61")
                return False
            
            # Data: FF 02 96 01 00 00 DD
            if not self._initial_96([0x01, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_96")
                return False
            
            # Data: FF 02 96 02 00 03 DD
            if not self._initial_96([0x02, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_96")
                return False
            
            # Data: FF 03 9A 01 08 00 A7 5D
            if not self._initial_9A([0x01, 0x08, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_9A")
                return False
            
            # Data: FF 03 9A 01 00 01 AF 5C
            if not self._initial_9A([0x01, 0x00, 0x01]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_9A")
                return False
            
            # Data: FF 02 6A 01 04 2E 4A
            if not self._initial_6A([0x01, 0x04]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_6A")
                return False
            
            # Data: FF 00 63 1D 6C
            if not self._initial_63():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_63")
                return False
            
            # Data: FF 01 62 01 BE BC
            if not self._initial_62():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_62")
                return False
            
            # Data: FF 01 62 01 BE BC
            if not self._initial_62():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_62")
                return False
            
            # Data: FF 02 6B 05 00 3A 6F
            if not self._initial_6B([0x05, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_6B")
                return False
            
            # Data: FF 01 61 05 BD B8
            if not self._initial_61():
                self.logger.error(f"{self.rfid_name} Failed to write _initial_61")
                return False

            #------------- Connect COM Port finish --------------------------------------

            # # Step 2: Configure basic parameters
            # if not self._configure_basic_parameters():
            #     print("Failed to configure basic parameters")
            #     return False
                
            # # Step 3: Set antenna parameters
            # if not self._configure_antenna():
            #     print("Failed to configure antenna")
            #     return False

            self.logger.info(f"{self.rfid_name} RFID Reader initialized successfully")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Reader initialization failed: {e}")
            return False

    def start_tag_reading(self, port_no: int) -> bool:
        """
        Start Tag Reading Process
        """
        self.logger.info(f"{self.rfid_name} === Start tag reading ===")

        try:
            # Data: FF 02 6A 01 00 2E 4E
            if not self._initial_6A([0x01, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_6A")
                return False
            
            # Data: FF 02 6A 01 08 2E 46
            if not self._initial_6A([0x01, 0x08]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_6A")
                return False

            # Data: FF 02 6A 01 06 2E 48
            if not self._initial_6A([0x01, 0x06]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_6A")
                return False

            # Data: FF 03 91 02 04 04 47 C0
            if not self._initial_91([0x02, port_no, port_no]):
                self.logger.error(f"{self.rfid_name} Failed to write _initial_91")
                return False
            
            # Data: FF 13 AA 4D 6F 64 75 6C 65 74 65 63 68 AA 48 00 16 00 80 00 88 BB BC 6D
            if not self._start_asynchronous_inventory([0x00, 0x16, 0x00, 0x80, 0x00]):
                self.logger.error(f"{self.rfid_name} Failed to write _start_asynchronous_inventory")
                return False

            self.logger.info(f"{self.rfid_name} Start tag reading successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Start tag reading failed: {e}")
            return False
        
    def stop_tag_reading(self) -> bool:
        """
        Stop Tag Reading Process
        """
        self.logger.info(f"{self.rfid_name} === Stop tag reading ===")
        
        try:
            if not self._stop_asynchronous_inventory():
                self.logger.error(f"{self.rfid_name} Failed to write _stop_asynchronous_inventory")
                return False

            self.logger.info(f"{self.rfid_name} Stop tag reading successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Stop tag reading failed: {e}")
            return False
        
    def read_tag(self) -> bool:
        """Read rfid tag"""
        try:
            # Reading rfid tag
            
            rfids = []
            i = 0
            while i < 5:
                response = self.dev_rs485.receive_command(timeout=10.0)
                
                if response and response.is_valid:
                    if response.is_heartbeat_response():
                        self.logger.info(f"{self.rfid_name} Received heartbeat response, ignoring...")
                        continue
                    metadata_flag = response.data[0] << 8 | response.data[1]
                    tag = self._parse_inventory_response(response, metadata_flag)
                    if tag:
                        metadata = tag.get('metadata', {})
                        self.logger.info(f"{self.rfid_name} EPC: {tag.get('epc', '')}, EPC Bytes: {tag.get('epc_bytes', b'').hex().upper()}, RSSI: {metadata.get('rssi', 0)}, Antenna ID: {metadata.get('antenna_id', 0)}, Timestamp: {metadata.get('timestamp', 0)}, PC Word: {tag.get('pc_word', 0):04X}, Tag CRC: {tag.get('tag_crc', 0):04X}")
                    rfid = tag.get('epc', '') if tag else ''
                    # rfid = response.data[11:-2]
                    # rfid = bytearray(response.data)[11:-2].decode('utf-8', errors='replace')
                    # rfid = ''.join(list(response.data)[11:-2])
                    # print(f'rfid={[f"{b:02X}" for b in rfid]}')
                    # print(f"Read tag successfully rfid={rfid.hex().upper()}")
                    self.logger.info(f"{self.rfid_name} Read tag rfid={rfid}")
                    rfids.append(rfid)
                else:
                    self.logger.error(f"{self.rfid_name} Failed to read tag")
                    rfids.append('')
                i += 1
            self.logger.info(f"{self.rfid_name} Read tags: {rfids}")
            return rfids
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting read tag: {e}")
            return None
    
    def _unknown_command(self) -> bool:
        """Handle unknown commands"""
        try:
            response = self.dev_rs485.send_direct_command(cmd_bytes = bytes([0x49, 0x4F, 0x47, 0x45, 0x54]))
            if response:
                self.logger.info(f"{self.rfid_name} _unknown_command handled successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to handle _unknown_command")
                return False
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error handling _unknown_command: {e}")
            return False
        
    def _unknown_command_00(self) -> bool:
        """Handle unknown commands"""
        try:
            zero_bytes = [0x00] * 255
            zero_bytes[0] = 0xFF
            zero_bytes[1] = 0xFA
            response = self.dev_rs485.send_direct_command(cmd_bytes = bytes(zero_bytes))
            if response:
                self.logger.info(f"{self.rfid_name} _unknown_command_00 handled successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to handle _unknown_command_00")
                return False
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error handling _unknown_command_00: {e}")
            return False
        
    def _reset_serial_buffer(self) -> bool:
        """reset_serial_buffer"""
        try:
            response = self.dev_rs485.reset_buffer()
            if response:
                self.logger.info(f"{self.rfid_name} _reset_serial_buffer handled successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to handle _reset_serial_buffer")
                return False
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error handling _reset_serial_buffer: {e}")
            return False

    def _stop_asynchronous_inventory(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # Data: FF 0E AA 4D 6F 64 75 6C 65 74 65 63 68 AA 49 F3 BB 03 91
            cmd = UHFCommand(UHFCommand.STOP_ASYNCHRONOUS_INVENTORY, is_extended=True)
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _stop_asynchronous_inventory retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _stop_asynchronous_inventory")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting reader info: {e}")
            return False
        
    def _start_asynchronous_inventory(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # Based on rs232.txt analysis: subcommand 0x49F3
            # cmd = UHFCommand(UHFCommand.EXTENDED_CMD_CODE, is_extended=True)
            cmd = UHFCommand(UHFCommand.START_ASYNCHRONOUS_INVENTORY, data=bytes(data), is_extended=True)
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _start_asynchronous_inventory retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _start_asynchronous_inventory")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _start_asynchronous_inventory: {e}")
            return False
        
    def _initial_03(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 00 03 1D 0C
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_03)
            response = self.dev_rs485.send_command(cmd, timeout=10.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_03 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_03")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_03: {e}")
            return False
        
    def _initial_04(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_04)
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_04 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_04")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_04: {e}")
            return False
        
    def _initial_06(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 04 06 00 01 C2 00 A4 60
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_06, data=bytes([0x00, 0x01, 0xC2, 0x00]))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_06 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_06")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_06: {e}")
            return False
        
    def _initial_61(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 01 61 05 BD B8
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_61, data=bytes([0x05]))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_61 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_61")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_61: {e}")
            return False
        
    def _initial_96(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 02 96 01 00 00 DD
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_96, data=bytes(data))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_96 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_96")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_96: {e}")
            return False
        
    def _initial_9A(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 03 9A 01 08 00 A7 5D
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_9A, data=bytes(data))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_9A retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_9A")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_9A: {e}")
            return False
        
    def _initial_6A(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 02 6A 01 04 2E 4A
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_6A, data=bytes(data))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_6A retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_6A")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_6A: {e}")
            return False
        
    def _initial_62(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 01 62 01 BE BC
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_62, data=bytes([0x01]))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_62 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_62")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_62: {e}")
            return False
        
    def _initial_63(self) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 00 63 1D 6C
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_63)
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_63 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_63")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_63: {e}")
            return False
        
    def _initial_6B(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 02 6B 05 00 3A 6F
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_6B, data=bytes(data))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_6B retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_6B")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_6B: {e}")
            return False
        
    def _initial_91(self, data) -> bool:
        """Get reader firmware version and information"""
        try:
            # Extended command for reader information
            # FF 03 91 02 04 04 47 C0
            cmd = UHFCommand(command_code=UHFCommand.INITIALIZE_91, data=bytes(data))
            response = self.dev_rs485.send_command(cmd, timeout=5.0)
            
            if response and response.is_valid:
                self.logger.info(f"{self.rfid_name} _initial_91 retrieved successfully")
                return True
            else:
                self.logger.error(f"{self.rfid_name} Failed to get _initial_91")
                return False
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error getting _initial_91: {e}")
            return False
    
    def inventory_tags(self, inventory_time_ms: int = 1000, metadata_flags: int = 0) -> Optional[List[Dict[str, Any]]]:
        """
        Perform tag inventory using standard inventory command (0x22)
        
        Args:
            inventory_time_ms: Inventory time in milliseconds
            metadata_flags: Metadata flags to request additional tag information
            
        Returns:
            List of dictionaries containing tag EPCs and metadata, or None if failed
        """
        if not self.is_initialized:
            self.logger.error("Reader not initialized. Call initialize_reader() first.")
            return None
            
        try:
            self.logger.info(f"Starting inventory (duration: {inventory_time_ms}ms, metadata_flags: 0x{metadata_flags:04X})")

            # Prepare inventory command data (inventory time in big-endian + metadata flags)
            time_high = (inventory_time_ms >> 8) & 0xFF
            time_low = inventory_time_ms & 0xFF
            flags_high = (metadata_flags >> 8) & 0xFF
            flags_low = metadata_flags & 0xFF
            inventory_data = bytes([time_high, time_low, flags_high, flags_low])
            
            # Create and send inventory command
            inventory_cmd = UHFCommand(UHFCommand.INVENTORY_CMD, inventory_data)
            timeout = 5.0 + (inventory_time_ms / 1000.0)  # Protocol specified timeout
            
            response = self.dev_rs485.send_command(inventory_cmd, timeout=timeout)
            
            if response and response.is_valid:
                tags = self._parse_inventory_response(response, metadata_flags)
                if tags:
                    print(f"✅ Found {len(tags)} tag(s)")
                    for i, tag_info in enumerate(tags, 1):
                        epc = tag_info.get('epc', 'Unknown')
                        print(f"   Tag {i}: {epc}")
                        if 'metadata' in tag_info:
                            metadata = tag_info['metadata']
                            if 'rssi' in metadata:
                                print(f"      RSSI: {metadata['rssi']} dBm")
                            if 'antenna_id' in metadata:
                                print(f"      Antenna: {metadata['antenna_id']}")
                else:
                    print("No tags found")
                return tags
            else:
                print("❌ Inventory command failed")
                return None
                
        except Exception as e:
            print(f"Error during inventory: {e}")
            return None
    
    # def _parse_inventory_response(self, response: UHFResponse, metadata_flags: int = 0) -> List[Dict[str, Any]]:
    def _parse_inventory_response(self, response: UHFResponse, metadata_flags: int = 0) -> Dict[str, Any]:
        """Parse inventory response to extract tag EPCs and metadata"""
        # tags = []
        tags = {}
        
        try:
            if not response.data:
                return tags
                
            # Parse tag data from response
            data = response.data
            offset = 0
            
            while offset < len(data):
                tag_info = {}
                
                # Parse metadata for this tag if flags are set
                if metadata_flags > 0:
                    metadata = response.parse_metadata(metadata_flags)
                    if metadata:
                        tag_metadata_offset = metadata.get('data_offset', 0)
                        # Remove data_offset from metadata as it's internal
                        metadata_copy = metadata.copy()
                        metadata_copy.pop('data_offset', None)
                        tag_info['metadata'] = metadata_copy
                        offset += tag_metadata_offset
                    else:
                        # If metadata parsing failed, assume no metadata for this tag
                        pass
                
                # For 0xAA command (asynchronous inventory), EPC length is 1 byte
                # This is the byte length of PC+EPC+TagCRC
                if offset + 1 <= len(data):
                    epc_total_length = data[offset]
                    offset += 1
                    
                    # Validate that we have enough data for this tag
                    if offset + epc_total_length > len(data):
                        break
                    
                    # PC Word (2 bytes)
                    pc_word = (data[offset] << 8) | data[offset + 1]
                    tag_info['pc_word'] = pc_word
                    offset += 2
                    
                    # Calculate EPC data length (total_length - PC(2) - CRC(2))
                    epc_data_length = epc_total_length - 4
                    if epc_data_length > 0:
                        # EPC ID
                        epc_data = data[offset:offset + epc_data_length]
                        # tag_info['epc'] = epc_data.hex().upper()
                        tag_info['epc'] = epc_data.decode('utf-8', errors='replace')
                        tag_info['epc_bytes'] = epc_data
                        # tag_info['epc_bytes'] = epc_data.hex().upper()
                        offset += epc_data_length
                        
                        # Tag CRC (2 bytes)
                        tag_crc = (data[offset] << 8) | data[offset + 1]
                        tag_info['tag_crc'] = tag_crc
                        offset += 2
                        
                        # tags.append(tag_info)
                        tags = tag_info
                    else:
                        # Invalid EPC length, skip this tag
                        offset += epc_total_length - 2  # Skip remaining data
                else:
                    break
                    
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error parsing inventory response: {e}")
            
        return tags
    
    def read_tag_data(self, epc: str, bank: int = 1, start_addr: int = 0, length: int = 6) -> Optional[bytes]:
        """
        Read data from specific tag
        
        Args:
            epc: Tag EPC in hex string format
            bank: Memory bank (0=Reserved, 1=EPC, 2=TID, 3=User)
            start_addr: Start address in bank
            length: Number of words to read
            
        Returns:
            Read data as bytes or None if failed
        """
        if not self.is_initialized:
            self.logger.error(f"{self.rfid_name} Reader not initialized. Call initialize_reader() first.")
            return None
            
        try:
            self.logger.info(f"{self.rfid_name} Reading tag data: EPC={epc}, Bank={bank}, Addr={start_addr}, Len={length}")

            # Convert EPC string to bytes
            epc_bytes = bytes.fromhex(epc)
            epc_length = len(epc_bytes)
            
            # Build read command data
            read_data = bytes([
                bank,  # Memory bank
                start_addr,  # Start address
                length,  # Length in words
                epc_length  # EPC length
            ]) + epc_bytes
            
            # Create and send read command
            read_cmd = UHFCommand(UHFCommand.READ_DATA_CMD, read_data)
            response = self.dev_rs485.send_command(read_cmd)
            
            if response and response.is_valid:
                # Parse read response
                if response.data and len(response.data) > 0:
                    self.logger.info(f"{self.rfid_name} Read successful: {response.data.hex().upper()}")
                    return response.data
                else:
                    self.logger.error(f"{self.rfid_name} No data in read response")
                    return None
            else:
                self.logger.error(f"{self.rfid_name} Read command failed")
                return None
                
        except Exception as e:
            self.logger.error(f"{self.rfid_name} Error reading tag data: {e}")
            return None



if __name__ == '__main__':
    #sun1 = Sunion('/dev/ttyAMA0', 4)
    # sun1 = Sunion('/dev/ttyUSB1', 4)
    sun1 = SunionUHF_SL('COM14', 4)
    sun1.daemon = True
    sun1.start()
    while True:
        for num in range(sun1.trycount):
            print(num+1, sun1.rfids[num], sun1.sensors[num])

        print('-'*20)
        time.sleep(1)
