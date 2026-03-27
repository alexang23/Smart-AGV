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

ANT_ON = bytes([0,0,1])
ANT_OFF = bytes([0,0,0])
ANT_READ = bytes([1,244])

import queue
import schedule

class SerialPortHandler:
    def __init__(self, port='COM14', baudrate=115200, timeout=0.5, max_queue_size=200):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.ser.reset_input_buffer()
        time.sleep(2)  # Give time for connection

        # Queues
        self.incoming_queue = queue.Queue(maxsize=max_queue_size)
        self.outgoing_queue = queue.Queue()

        self.running = False

        # Threads
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)

    def start(self):
        if not self.ser.is_open:
            self.ser.open()
            self.ser.reset_input_buffer()
            time.sleep(2)  # Give time for connection
        self.running = True
        self.reader_thread.start()
        self.writer_thread.start()

    def stop(self):
        self.running = False
        self.reader_thread.join()
        self.writer_thread.join()
        self.ser.close()

    def _read_loop(self):
        while self.running:
            # if self.ser.in_waiting: # cause very high CPU usage
                # line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            line = self.ser.readline()
            # print(f"_read_loop : {line}")
            if line:
                try:
                    self.incoming_queue.put_nowait(line)
                except queue.Full:
                    print("Warning: Incoming queue full. Dropping line.")

    def _write_loop(self):
        while self.running:
            try:
                # Wait for item, but allow graceful shutdown
                data = self.outgoing_queue.get(timeout=0.1)
                if self.ser.is_open:
                    # self.ser.write((data + '\n').encode())
                    self.ser.write(data)
            except queue.Empty:
                continue

    def write(self, data):
        """Queue data to be written asynchronously."""
        self.outgoing_queue.put(data)

    def read(self, block=True, timeout=None):
        """Read a line from incoming queue."""
        try:
            return self.incoming_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    # def send_and_wait(self, cmd, matcher=None, timeout=5):
    def send_and_wait(self, cmd, timeout=5):
        """
        Send a command and wait for a matching response.
        matcher: a callable that takes a line and returns True if it's the response you're looking for.
        """
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} send : {list(cmd)}')
        self.write(cmd)
        end_time = time.time() + timeout
        # return_line = None
        while time.time() < end_time:
            try:
                line = self.read(timeout=0.5)
                # if line and (matcher is None or matcher(line)):
                if line:
                    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} recv : {list(line)}')
                    recv = list(line)
                    if recv[0] == 165:
                        # return_line = line
                        return line
                else:
                    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} recv : {line}')
                    # if return_line:
                    #     return return_line
            except queue.Empty:
                pass
        raise TimeoutError(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} Timeout waiting for response to: {list(cmd)}')

class SunionUHF_RS(threading.Thread):
    def __init__(self, devPath, type='UHF_RS', controller=None, event_mgr=None, trycount=10, pickcount=3, timeout=500):
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
        
        try:
            self.dev_rs485 = SerialPortHandler(self.devPath)
            self.dev_rs485.start()
        except Exception as err:
            self.logger.error(str(err))
            self.dev_rs485 = None



    def get_most_common_rfid(self, rfid_list):
        # [b'000008M10013', b'000008M10013', b'000008M10013', None, None, None, b'000008M10013', b'000008M10013', b'000008M10013', None]

        # Filter strings with length 12
        # filtered = [s for s in rfid_list if len(s) == 12] can not use for None

        filtered = []
        for item in rfid_list:
            if item is None or not item:
                continue
            # if isinstance(item, bytes):
            #     item = item.decode('utf-8', errors='ignore')
            if len(item) == 12:
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

    def cmd_read(self, port_no=1):
        # cmd = 'K0'
        # header = 'S0%d%s'%(rfid_config['dev ID'], cmd)
        # # data = '%02XM%02d'%(port_id, rfid_config['read_page_nums'])
        # data = '%02XM%02d'%(port_id, read_page)

        try:

            print('start read UHF')

            cmd = self.UHF_cmd(40, ANT_ON, 3)
            # output = send_cmd.encode('utf-8') # python3
            # self.dev_rs485.write(cmd)
            resp = self.dev_rs485.send_and_wait(cmd)
            # print(f"resp = {list(resp)}")

            # bytes_buf = self.dev_rs485.read(1024) 
            # # byte = byte.decode("utf-8") # python3
            # # print(byte.hex())
            # recv_buf = list(bytes_buf)
            # print(f"{len(recv_buf)}, {recv_buf}")
            # self.UHF_read_decode(recv_buf, len(recv_buf))
            # if bytes_buf == '':
            #     print('serial read timeout')
                # time.sleep(0.05)
                # try_count += 1
                # if try_count > 30:
                #     break
                # else:
                #     continue  
            # rec_data += byte
            time.sleep(1)
            for i in range(self.trycount):
                print(f"try read {i}")
                # ant_off = b'00000000000'
                # read_uhf = bytes([165,90,0,10,128,1,244,127,13,10])
                # cmd = self.UHF_cmd(128, read_uhf, 10, 3, True)
                cmd = self.UHF_cmd(128, ANT_READ, 2)
                # output = send_cmd.encode('utf-8') # python3
                # self.dev_rs485.write(send_cmd)
                resp = self.dev_rs485.send_and_wait(cmd)
                # print(f"resp = {list(resp)}")
                self.tmp_rfids[port_no-1][i] = self.UHF_read_decode(resp, len(resp))
                # bytes_buf = self.dev_rs485.read(1024)
                # recv_buf = list(bytes_buf)
                # print(f"{len(recv_buf)}, {recv_buf}")
                # self.UHF_read_decode(recv_buf, len(recv_buf))
                # time.sleep(1)
            print(self.tmp_rfids)
            # time.sleep(3)
            # ant_off = b'00000000000'
            cmd = self.UHF_cmd(40, ANT_OFF, 3)
            # output = send_cmd.encode('utf-8') # python3
            # self.dev_rs485.write(send_cmd)
            resp = self.dev_rs485.send_and_wait(cmd)
            # print(f"resp = {list(resp)}")
            # bytes_buf = self.dev_rs485.read(1024)
            # recv_buf = list(bytes_buf)
            # print(f"{len(recv_buf)}, {recv_buf}")
            # self.UHF_read_decode(recv_buf, len(recv_buf))

            print('end read UHF')

            rfid_value = self.get_most_common_rfid(self.tmp_rfids[port_no-1])
            self.prev_rfids[port_no-1] = self.rfids[port_no-1]
            if rfid_value:
                self.rfids[port_no-1] = rfid_value.decode('utf-8')[-8:]
            else:
                self.rfids[port_no-1] = ''

            if self.prev_rfids[port_no-1] != self.rfids[port_no-1]:
                if self.rfids[port_no-1]:
                    self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=1, msg_text='place rfid', server=True)
                else:
                    self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text='remove rfid', server=True)
            
            # print(f"UHF RFID value={self.rfids[port_no-1]}, prev value={self.prev_rfids[port_no-1]}")
            self.logger.info(f"prev_carrier_id={self.prev_rfids[port_no-1]}, carrier_id={self.rfids[port_no-1]}")

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


    
    def checksum(self, array_buf: bytearray, len_array_buf: int) -> int:
        b = 0
        for i in range(2, len_array_buf):
            b ^= array_buf[i]
        return b

    def UHF_cmd(self, cmd: int, cmd_buf: bytes, len_cmd_buf: int) -> bytearray:
        array = bytearray(1024)
        array[0] = 165
        array[1] = 90

        num = 4
        num2 = 5

        array[num] = cmd & 0xFF

        for i in range(len_cmd_buf):
            array[num2] = cmd_buf[i]
            num2 += 1

        num3 = num2
        num2 += 1

        array[num2] = 13  # \r
        num2 += 1
        array[num2] = 10  # \n
        num2 += 1

        array[2] = (num2 >> 8) & 0xFF
        array[3] = num2 & 0xFF

        array[num3] = self.checksum(array, num3)

        return array[:num2]

    def UHF_read_decode(self, recv_buf, recv_count):
        # try:
            text = ""
            # num = int(comboBox_10_text) # Write UHF tag used

            if recv_count > 8:
                for i in range(recv_count - 1):
                    # 0: 165, A5, 1010 0101, 1:90, 5A, 0101 1010
                    num2 = recv_buf[i] << 8 | recv_buf[i + 1]
                    if num2 == 3338: # D0A  last-1:13, D, 1101, last:10, A, 1010
                        num3 = recv_buf[0] << 8 | recv_buf[1]
                        num4 = recv_buf[2] << 8 | recv_buf[3]
                        # print('line 272')
                        if num3 == 42330: # A55A
                            if recv_buf[4] not in [41, 129, 135]:
                                text = "undefined\n"
                                print(text)
                            elif recv_buf[4] == 135: # Write UHF tag
                                print('line 278')
                                pass
                                # if recv_buf[6] == 0:
                                #     text = "write rep ok\n"
                                #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "NO"
                                #     do_RFID_DELEGATE_0.ALARM_STATE = "00"
                                # elif recv_buf[6] == 1:
                                #     text = "no tag\n"
                                #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                                #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                                # elif recv_buf[6] == 2:
                                #     text = "password failed\n"
                                #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                                #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                                # elif recv_buf[6] == 3:
                                #     text = "write failed.\n"
                                #     method_73("RFID_LHF_WRITE")
                                #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                                #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                            elif recv_buf[4] == 129: # Read UHF tag
                                # print('line 298')
                                num5 = 0
                                text = f"sing read rep PC={recv_buf[5]:02X}{recv_buf[6]:02X}"
                                # print(f"{text}")
                                # text2 = bytes(recv_buf).decode('utf-8', errors='ignore')[7:19]
                                text2 = bytes(recv_buf[7:19])
                                # print(f"UHF rfid tag value : {text2}")
                                # uhf_ARRAY_PARA_0.id[uhf_ARRAY_PARA_0.now_po] = text2
                                # uhf_ARRAY_PARA_0.now_po += 1

                                num7 = 7
                                for _ in range(12):
                                    # text += f" {recv_buf[num7]:02X}"
                                    num7 += 1

                                # text += "\n"
                                num5 = recv_buf[num7] << 8 | recv_buf[num7 + 1]
                                num7 += 2
                                num8 = float(num5)
                                texta = f"RSSI = {num8 / 10.0:.2f}"
                                # print(texta)

                                num9 = recv_buf[num7]
                                textb = f"ch = {num9}"
                                # print(textb)

                                print(f"UHF rfid tag value : {text2}, {textb}, {texta}, {text}")
                                return text2

                            elif recv_buf[4] == 41: # Set UHF ON/OFF
                                print('line 322')
                                if recv_buf[5] != 1:
                                    text = "ant set rep Fail"
                                    print(text)
                                else:
                                    text = "ant set rep OK"
                                    print(text)

                            # loadport_2.now_package.sender = False
                            # if text:
                            #     method_69("RFIDUFD", text)

                        # try:
                        #     for i in range(1024):
                        #         recv_buf[i] = 0
                        # finally:
                        #     recv_count = 0
        # except Exception as err:
        #     print(str(err))

    def UHF_read_decode_orig(comboBox_10_text, loadport_2, secs_RFID_0, do_RFID_DELEGATE_0, uhf_ARRAY_PARA_0, method_69, method_73):
        text = ""
        # num = int(comboBox_10_text) # Write UHF tag used

        if loadport_2.recv_count > 8:
            for i in range(loadport_2.recv_count - 1):
                # 0: 165, A5, 1010 0101, 1:90, 5A, 0101 1010
                num2 = loadport_2.recv_buf[i] << 8 | loadport_2.recv_buf[i + 1]
                if num2 == 3338: # D0A  last-1:13, D, 1101, last:10, A, 1010
                    num3 = loadport_2.recv_buf[0] << 8 | loadport_2.recv_buf[1]
                    num4 = loadport_2.recv_buf[2] << 8 | loadport_2.recv_buf[3]
                    if num3 == 42330: # A55A
                        if loadport_2.recv_buf[4] not in [41, 129, 135]:
                            text = "undefine\n"
                        elif loadport_2.recv_buf[4] == 135: # Write UHF tag
                            pass
                            # if loadport_2.recv_buf[6] == 0:
                            #     text = "write rep ok\n"
                            #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "NO"
                            #     do_RFID_DELEGATE_0.ALARM_STATE = "00"
                            # elif loadport_2.recv_buf[6] == 1:
                            #     text = "no tag\n"
                            #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                            #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                            # elif loadport_2.recv_buf[6] == 2:
                            #     text = "password failed\n"
                            #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                            #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                            # elif loadport_2.recv_buf[6] == 3:
                            #     text = "write failed.\n"
                            #     method_73("RFID_LHF_WRITE")
                            #     do_RFID_DELEGATE_0.SSACK = secs_RFID_0.string_0[num] = "TE"
                            #     do_RFID_DELEGATE_0.ALARM_STATE = "01"
                        elif loadport_2.recv_buf[4] == 129: # Read UHF tag
                            num5 = 0
                            text = f"sing read rep PC={loadport_2.recv_buf[5]:02X}{loadport_2.recv_buf[6]:02X}\n"
                            text2 = bytes(loadport_2.recv_buf).decode('utf-8', errors='ignore')[7:19]
                            uhf_ARRAY_PARA_0.id[uhf_ARRAY_PARA_0.now_po] = text2
                            uhf_ARRAY_PARA_0.now_po += 1

                            num7 = 7
                            for _ in range(12):
                                text += f" {loadport_2.recv_buf[num7]:02X}"
                                num7 += 1

                            text += "\n"
                            num5 = loadport_2.recv_buf[num7] << 8 | loadport_2.recv_buf[num7 + 1]
                            num7 += 2
                            num8 = float(num5)
                            text += f"RSSI = {num8 / 10.0:.2f}\n"

                            num9 = loadport_2.recv_buf[num7]
                            text += f"ch = {num9}\n"

                        elif loadport_2.recv_buf[4] == 41: # Set UHF ON/OFF
                            if loadport_2.recv_buf[5] != 1:
                                text = "ant set rep fail\n"
                            else:
                                text = "ant set rep ok\n"

                        loadport_2.now_package.sender = False
                        # if text:
                        #     method_69("RFIDUFD", text)

                    try:
                        for i in range(1024):
                            loadport_2.recv_buf[i] = 0
                    finally:
                        loadport_2.recv_count = 0


if __name__ == '__main__':
    #sun1 = Sunion('/dev/ttyAMA0', 4)
    # sun1 = Sunion('/dev/ttyUSB1', 4)
    sun1 = SunionUHF_RS('COM14', 4)
    sun1.daemon = True
    sun1.start()
    while True:
        for num in range(sun1.trycount):
            print(num+1, sun1.rfids[num], sun1.sensors[num])

        print('-'*20)
        time.sleep(1)
