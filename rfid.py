########################################
# sun1 = Sunion('/dev/ttyAMA0')
# sun1.daemon = True
# sun1.start()
########################################

import time
from time import sleep
import serial
import string
import binascii
import threading
import traceback
import collections
from collections import OrderedDict
from collections import Counter
import sys
import json
import re
from config import settings
from datetime import datetime
from global_log import Logger

SOH = 0x01
STX = 0x02
ETX = 0x03
BCC = 0x00

# class Sunion(threading.Thread):
class Sunion:
    def __init__(self, devPath, name='1', type='LF', controller=None, event_mgr=None, portNumber=4, trycount=3, pickcount=2):
        # threading.Thread.__init__(self)
        self.stop = False
        self.trycount = trycount
        self.pickcount = pickcount
        self.portNumber = portNumber
        self.sensors = [False]*portNumber
        self.prev_rfids = ['']*portNumber
        self.rfids = ['']*portNumber
        self.tmp_rfids = ['']*portNumber
        self.lastTime = [time.monotonic_ns()]*portNumber
        self.count = [0]*portNumber
        self.access_mode = [0]*portNumber
        self.controller = controller
        self.event_mgr = event_mgr
        self.devPath = devPath
        self.type = type
        self.rfid_name = f"rfid_{type}_{name}"
        self.page_num = settings.LF_RFID_READ_PAGE_NUMS
        self.dev_rs485 = None
        self.logger = Logger(f"rfid_{type}_{name}", f"rfid_{type}_{name}.log")
        self.receive_queue = collections.deque()
        self.svr_enable = True
        self.reconnect = False
        self.last_update = time.time()

        try:
            self.dev_rs485 = serial.Serial(self.devPath, 9600, 8, 'N', 1, timeout=0.5)
            # self.dev_rs485.flushInput()
            self.dev_rs485.reset_input_buffer()
            self.logger.info(f"{self.rfid_name} connect device")
            self.send_event(True, 0, 0, 'connect')
            
            # for m in range(len(self.rfids)):
            #     self.sync_read(m+1)
            #     # print(f"rfid {m+1} : {self.rfids[m]}")
        except Exception as err:
            self.logger.error(f"{self.rfid_name} connect error={str(err)}")
            self.send_event(True, 128, 1, 'could not open port')
            self.dev_rs485 = None

    def cmd_beep(self):
        cmd = 'B3'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        self.write_sunion(header)
        return self.read_sunion()

    def cmd_read_setting(self):
        cmd = 'J3'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        data = '%02d%02d%02d%02d%02d%02d%02d'\
            %(settings.LF_RFID_READ_RF_TIMEOUT, 
            settings.LF_RFID_READ_BEEP, 
            settings.LF_RFID_INITIAL_PAGE, 
            settings.LF_RFID_READ_PAGE_NUMS, 
            settings.LF_RFID_READ_MODE, 
            settings.LF_RFID_REGULAR_READ_TIME, 
            settings.LF_RFID_READ_TIME)
        self.write_sunion(header, data)
        return self.read_sunion()

    def cmd_read(self, port_id = 1, read_page = 1):
        cmd = 'K0'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        # data = '%02XM%02d'%(port_id, settings.LF_RFID_READ_PAGE_NUMS)
        data = '%02XM%02d'%(port_id, read_page)
        self.write_sunion(header, data)
        res = self.read_sunion()
        if type(res) == str:
            return res[::-1]
        else:
            return ''

    def cmd_write(self, rfid_id, port_id = 1, page_num = 1):   
        cmd = 'K1'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        data = '%02XM%02d%08s'%(port_id, page_num, rfid_id)
        self.write_sunion(header, data)
        return self.read_sunion()

    def cmd_ir_read(self, port_id = 1): # 1-12
        cmd = 'A1'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        data = '%02X'%(port_id)
        self.write_sunion(header, data)
        # return self.read_sunion()
        res = self.read_sunion()
        if type(res) == tuple:
            return res
        else:
            return '', -1
    
    def reread(self, devID = 1,port_id = 1):
        cmd = 'A2'
        header = 'S0%d%s'%(devID, cmd)
        data = '%02X'%(port_id)
        self.write_sunion(header, data)
        return self.read_sunion()

    def cmd_all_ir_read(self):   
        cmd = 'A3'
        header = 'S0%d%s'%(settings.LF_RFID_DEV_ID, cmd)
        self.write_sunion(header)
        return self.read_sunion()

    ####################
    def write_sunion(self, *cmd):
        try:
            # print('write RFID cmd : ', cmd)
            output = chr(SOH)
            output += cmd[0]
            output += chr(STX)
            if len(cmd) >= 2:
                output += cmd[1]
            output += chr(ETX)
            BCC = self.calBcc(output)
            output += chr(BCC)
            output = output.encode('utf-8') # python3
            self.dev_rs485.write(output)
        except Exception as err:
            self.logger.error(f"{self.rfid_name} write_sunion : {str(err)}")
            self.reconnect = True

    def calBcc(self, data):  
        bcc = ord(data[0])
        for var in data[1:]:
            bcc ^= ord(var)
        bcc |= 0x20
        return bcc

    def read_sunion(self):
        # return False
        rec_data = ''
        try_count = 0
        first_pack = True
        id_len = settings.LF_RFID_LENGTH
        while True:
            try:
                byte = self.dev_rs485.read() 
                byte = byte.decode("utf-8") # python3
            except Exception as err:
                self.logger.error(f"{self.rfid_name} read_sunion : byte.decode {str(err)}")
                # break
                self.reconnect = True
                return False
            if byte == '':
                print('serial read timeout')
                time.sleep(0.05)
                try_count += 1
                # if try_count > 30:
                if try_count >= 1:
                    break
                else:
                    continue
            rec_data += byte

            if settings.LF_RFID_DATA_TYPE:
                try:
                    if byte == chr(ETX):
                        bcc = self.dev_rs485.read().decode("utf-8") # BCC
                        # bcc = self.dev_rs485.read() # BCC
                        #print('get : ',rec_data)
                        if bcc == chr(self.calBcc(rec_data)):
                            #print('check bcc success')
                            return self.cct_decode(rec_data)
                        else:
                            print('bcc fail')
                            # break
                            return False
                except Exception as err:
                    self.logger.error(f"{self.rfid_name} read_sunion : data_type=1, error={str(err)}")
                    # break
                    return False
            else:
                try:
                    if len(rec_data) >= 12 + id_len: # \x01 s 0 1 A 1 \x02 0 1 M 1 \x03
                        bcc = self.dev_rs485.read() # BCC
                        if bcc == chr(self.calBcc(rec_data)):
                            return self.cct_decode(rec_data)
                        else:
                            print('bcc fail')
                            # break
                            return False
                except Exception as err:
                    self.logger.error(f"{self.rfid_name} read_sunion : data_type=0, error={str(err)}")
                    # break
                    return False
        return False

    def cct_decode(self, rec_data):
        #print('data:', rec_data)
        pos_SOH = rec_data.find(chr(SOH))
        pos_STX = rec_data.find(chr(STX))
        pos_ETX = rec_data.find(chr(ETX))
        cmd = rec_data[pos_SOH + 4 : pos_STX]
        data = rec_data[pos_STX + 1 : pos_ETX] if settings.LF_RFID_DATA_TYPE else rec_data[pos_STX + 1 : -1]
        #print('cmd: ', cmd)
        #print('data: ', data)
        if data == 'Y': # cmd = B3, J3, K1
            return True
        elif data == 'N':
            return False
        elif cmd == 'K0': # manual read page without IR sensor
            rfid = data[6:]
            rfid = '' if rfid == '-'*len(rfid) or rfid == '\x00'*len(rfid) else rfid
            rfid =  rfid if settings.LF_RFID_DATA_TYPE else binascii.hexlify(rfid)
            rfid = ''.join(reversed(rfid))
            # rfid = ''.join(reversed(rfid)) if settings.LF_RFID_ORDER else ''.join(rfid)
            # rfid = ''.join(rfid)
            if type(rfid) != str: # python2
                #rfid = rfid.decode('utf-8')
                rfid = filter(lambda x: x in string.printable, rfid)
            else:   # python3
                rfid = ''.join(x for x in rfid if x.isprintable())
            return rfid
        elif cmd == 'A1': # auto read page with IR sensor
            #pos = int(data[:2], 16)-1
            rfid = data[4:]
            rfid = '' if rfid == '-'*len(rfid) or rfid == '\x00'*len(rfid) else rfid
            rfid =  rfid if settings.LF_RFID_DATA_TYPE else binascii.hexlify(rfid)
            # rfid = ''.join(reversed(rfid)) if settings.LF_RFID_ORDER else ''.join(rfid)
            rfid = ''.join(rfid)
            if type(rfid) != str: # python2
                #rfid = rfid.decode('utf-8')
                rfid = filter(lambda x: x in string.printable, rfid)
            else:   # python3
                rfid = ''.join(x for x in rfid if x.isprintable())
            ir =  data[3:4]
            return rfid, ir
            #return pos, rfid, ir
        elif cmd == 'A3':
            #print(data)
            #all_ir = data
            return data
        
    def check_all_same(self, input_list):
        # Check if all elements in the list are the same
        return all(element == input_list[0] for element in input_list)
    
    def send_event(self, server=False, code=0, subcode=0, msg_text=None, board=1):
        try:
            data = OrderedDict()

            if server:
                data['Server'] = True
            data['device_id'] = settings.DEVICE_ID
            data['board_id'] = self.rfid_name
            # data['port_no'] = self.port_no[cs]
            # data['port_id'] = self.port_id[cs]
            # data['port_state'] = self.port_status[cs]
            # data['eqp_state'] = self.controller.equipment_state
            # data['prev_carrier_id'] = self.prev_rfid_data[cs]
            # data['carrier_id'] = self.rfid_data[cs]
            # data['dual_port'] = cs
            # data['mode'] = self.mode[cs] # Access Mode 0: Unknown, 1: Auto, 2: Manual
            # data['load'] = self.load[cs]  # 0071 status
            # data['alarm_id'] = self.alarm_id[cs]
            # data['alarm_text'] = self.alarm_text[cs]
            data['type'] = 5
            # data['stream'] = -1
            # data['function'] = -1
            data['code_id'] = code
            data['sub_id'] = subcode
            data['msg_text'] = msg_text
            # data['status'] = json.dumps(status)
            data['occurred_at'] = time.time()
            # data['version'] = f"{self.fw_version}, {settings.SW_VERSION}"
            data['version'] = f"{settings.SW_VERSION}"
            self.event_mgr.on_notify(data)

        except Exception as err:
            self.logger.error(str(err))
    
    def mqtt_publish_status(self, port_no, type=2, code=0, subcode=-1, msg_text='rfid LF init'):
        if not settings.MQTT_RFID_MSG_ENABLE:
            return
        
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
    
    # def mqtt_publish(self, port_no, rfid_data, type, code, subcode=-1, msg_text=None, server=False):
    #     data = {}
    #     if server:
    #         data['Server'] = True
    #     data['device_id'] = settings.DEVICE_ID
    #     data['port_id'] = str(port_no)
    #     data['port_no'] = port_no
    #     data['dual_port'] = 0
    #     if settings.RFID_DEVICE_ONLY:
    #         data['mode'] = 2 # Access Mode 0: Unknown, 1: Auto, 2: Manual
    #     else:
    #         data['mode'] = self.access_mode[port_no-1]
    #     data['carrier_id'] = rfid_data
    #     data['type'] = type
    #     data['stream'] = -1
    #     data['function'] = -1
    #     data['code_id'] = code
    #     data['sub_id'] = subcode
    #     data['msg_text'] = msg_text
    #     data['status'] = ''
    #     data['occurred_at'] = time.time()
    #     self.event_mgr.on_notify(data)

    def mqtt_publish(self, port_no, prev_rfid_data, rfid_data, type, code, subcode=-1, msg_text=None, server=False):
        if not settings.MQTT_RFID_MSG_ENABLE:
            return
        
        data = {}
        
        if server:
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

    def get_most_common_rfid(self, rfid_list, rfid_length=settings.LF_RFID_LENGTH):
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
        return '--------'
    
    def clear_rfid(self, port_no=1):
        self.logger.info(f"{self.rfid_name} port_no {port_no} : mode={self.access_mode[port_no-1]}, prev_rfid=[{self.prev_rfids[port_no-1]}], rfid=[{self.rfids[port_no-1]}]")
        self.logger.info(f"{self.rfid_name} port_no {port_no} : remove rfid [{self.rfids[port_no-1]}]")
        self.prev_rfids[port_no-1] = self.rfids[port_no-1]
        self.rfids[port_no-1] = ''
        self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text=f"remove rfid [{self.prev_rfids[port_no-1]}]", server=True)
        

    def sync_read(self, port_no, cs=0, rfid_length=settings.LF_RFID_LENGTH, rfid_order=settings.LF_RFID_ORDER, pattern=settings.RFID_CS0_PATTERN):
        tmp_rfids = []
        if rfid_length > 8:
            for i in range(settings.LF_RFID_TRY_COUNT):
                rfid_orig = ''
                for page in range(settings.LF_RFID_READ_PAGE_NUMS):
                    rfid_page = self.cmd_read(port_no + cs, page+1)
                    if type(rfid_page) == str:
                        rfid_orig += rfid_page
                tmp_rfids.append(rfid_orig)
                sleep(settings.LF_RFID_READ_INTERVAL_TIME/1000.0)
        else:
            for i in range(settings.LF_RFID_TRY_COUNT):
                rfid_orig = ''
                for page in range(1):
                    rfid_page = self.cmd_read(port_no + cs, page+1)
                    if type(rfid_page) == str:
                        rfid_orig += rfid_page
                tmp_rfids.append(rfid_orig)
                sleep(settings.LF_RFID_READ_INTERVAL_TIME/1000.0)
        
        self.logger.info(f"{self.rfid_name} port_no {port_no} : {tmp_rfids}")
        rfid_orig = self.get_most_common_rfid(tmp_rfids, rfid_length)
        # print(f"rfid_orig={rfid_orig}")
        # tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
        # print(f'#### {tsr} after read {rfid_orig}')

        if rfid_orig:
            rfid = rfid_orig[:rfid_length]
            rfid = ''.join(reversed(rfid)) if rfid_order else ''.join(rfid)
        else:
            rfid = rfid_orig

        if len(rfid) == rfid_length: # ps_sensor=1, rfid=xxxxxx, len=rfid_length
            if re.match(pattern, rfid):
                pass
            else:
                self.prev_rfids[port_no-1] = self.rfids[port_no-1]
                self.rfids[port_no-1] = rfid
                self.logger.error(f"{self.rfid_name} port_no {port_no} : place rfid [{rfid}] is incorrect")
                self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=128, subcode=1, msg_text=f"ps sensor 1, place rfid [{rfid}] is incorrect", server=True)
                return
        else: # ps_sensor=1, rfid=xxxxxx, len=not rfid_length
            self.prev_rfids[port_no-1] = self.rfids[port_no-1]
            self.rfids[port_no-1] = rfid
            self.logger.error(f"{self.rfid_name} port_no {port_no} : place rfid [{rfid}] length is not {rfid_length}")
            self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=128, subcode=2, msg_text=f"place rfid [{rfid}] length is not {settings.LF_RFID_LENGTH}", server=True)
            return
        
        # tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
        # tdiff = time.monotonic_ns() - self.lastTime[port_no-1]

        # if settings.RFID_DEBUG_ENABLE :
            # print(f'{tsr} {self.rfid_name} port_no {port_no} : mode={self.access_mode[port_no-1]}, prev_rfid=[{self.prev_rfids[port_no-1]}], rfid=[{self.rfids[port_no-1]}], new_rfid=[{rfid}] ({tdiff})')
            # self.logger.info(f"{self.rfid_name} port_no {portNum+1} : mode={self.access_mode[portNum]}, self.prev_rfid=[{self.prev_rfids[portNum]}], self.rfid=[{self.rfids[portNum]}], rfid=[{rfid}], tmp_rfid=[{self.tmp_rfids[portNum]}]")
        self.logger.info(f"{self.rfid_name} port_no {port_no} : mode={self.access_mode[port_no-1]}, prev_rfid=[{self.prev_rfids[port_no-1]}], rfid=[{self.rfids[port_no-1]}], new_rfid=[{rfid}]")

        if self.rfids[port_no-1] != rfid:
            # self.logger.info(f"{self.rfid_name} port_no {port_no} : send rfid [{rfid}]")
            if len(self.rfids[port_no-1]) == 0 and len(rfid) > 0:
                self.logger.info(f"{self.rfid_name} port_no {port_no} : place rfid [{rfid}]")
                self.prev_rfids[port_no-1] = self.rfids[port_no-1]
                self.rfids[port_no-1] = rfid
                self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=1, msg_text=f"place rfid [{self.rfids[port_no-1]}]", server=True)
            elif len(self.rfids[port_no-1]) > 0 and len(rfid) == 0:
                self.logger.info(f"{self.rfid_name} port_no {port_no} : remove rfid [{self.rfids[port_no-1]}]")
                self.prev_rfids[port_no-1] = self.rfids[port_no-1]
                self.rfids[port_no-1] = ''
                self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text=f"remove rfid [{self.prev_rfids[port_no-1]}]", server=True)
            else:
                self.logger.info(f"{self.rfid_name} port_no {port_no} : remove rfid [{self.rfids[port_no-1]}]")
                self.prev_rfids[port_no-1] = self.rfids[port_no-1]
                self.rfids[port_no-1] = ''
                self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=0, msg_text=f"remove rfid [{self.prev_rfids[port_no-1]}]", server=True)

                self.logger.info(f"{self.rfid_name} port_no {port_no} : place rfid [{rfid}]")
                self.prev_rfids[port_no-1] = self.rfids[port_no-1]
                self.rfids[port_no-1] = rfid
                self.mqtt_publish(port_no=port_no, prev_rfid_data=self.prev_rfids[port_no-1], rfid_data=self.rfids[port_no-1], type=2, code=0, subcode=1, msg_text=f"place rfid [{self.rfids[port_no-1]}]", server=True)

class SunionPS(Sunion, threading.Thread):
    def __init__(self, devPath, name='1', type='LF', controller=None, event_mgr=None, portNumber=4, trycount=3, pickcount=2):
        Sunion.__init__(self, devPath=devPath, name=name, type=type, controller=controller, event_mgr=event_mgr, portNumber=portNumber, trycount=trycount, pickcount=pickcount)
        threading.Thread.__init__(self)
        # self.stop = False
        # self.trycount = trycount
        # self.pickcount = pickcount
        # self.portNumber = portNumber
        # self.sensors = [False]*portNumber
        # self.prev_rfids = ['']*portNumber
        # self.rfids = ['']*portNumber
        # self.tmp_rfids = ['']*portNumber
        # self.lastTime = [time.monotonic_ns()]*portNumber
        # self.count = [0]*portNumber
        # self.access_mode = [0]*portNumber
        # self.event_mgr = event_mgr
        # self.devPath = devPath
        # self.type = type
        # self.rfid_name = f"rfid_{type}_{name}"
        # self.page_num = settings.LF_RFID_READ_PAGE_NUMS
        # self.dev_rs485 = None
        # self.logger = Logger(f"rfid_{type}_{name}", f"rfid_{type}_{name}.log")
        # self.receive_queue = collections.deque()
        # self.svr_enable = True

        # try:
        #     self.dev_rs485 = serial.Serial(self.devPath, 9600, 8, 'N', 1, timeout=0.5)
        #     # self.dev_rs485.flushInput()
        #     self.dev_rs485.reset_input_buffer()
        #     # for m in range(len(self.rfids)):
        #     #     self.sync_read(m+1)
        #     #     # print(f"rfid {m+1} : {self.rfids[m]}")
        # except Exception as err:
        #     self.logger.error(str(err))
        #     self.dev_rs485 = None

    def run(self):
        self.logger.info(f"RFID LF Starting")
        while not self.stop:
            if self.dev_rs485 == None:
                try:
                    self.dev_rs485 = serial.Serial(self.devPath, 9600, 8, 'N', 1, timeout=0.5)
                    # self.dev_rs485.flushInput()
                    self.dev_rs485.reset_input_buffer()
                    self.logger.info(f"{self.rfid_name} connect device")
                    self.send_event(True, 0, 0, 'connect')
                except Exception as err:
                    self.logger.error(f"{self.rfid_name} connect error={str(err)}")
                    self.send_event(True, 128, 1, 'could not open port')
                    self.dev_rs485 = None
                    time.sleep(10)
            else:
                try:
                    # pattern = r'^[0-9]{2}[0-9A-Z][BC][0-9]{5}$'
                    pattern = settings.RFID_CS0_PATTERN
                    for portNum in range(self.portNumber):
                        if settings.RFID_READ_PS_ENABLE:
                            rfid_orig, ps_sensor = self.cmd_ir_read(portNum+1)
                            # ps_sensor is str, rfid is str
                            # print('loadport:{} ps_sensor:{} rfid:{}'.format(portNum+1, ps_sensor, rfid))
                            # rfid = self.cmd_read(portNum+1)
                            # self.logger.info(f"{self.rfid_name} port_no {portNum+1} : ps_sensor={ps_sensor}, rfid_orig={rfid_orig}")

                            if self.reconnect:
                                break

                            if ps_sensor not in ['0', '1']:
                                self.reconnect = True
                                break

                            if type(rfid_orig) != str:
                                self.logger.error(f"{self.rfid_name} port_no {portNum+1} : rfid orig type error.")
                                continue
                            
                            if len(rfid_orig) == 0:
                                rfid = rfid_orig
                            else:
                                if len(rfid_orig) < settings.LF_RFID_LENGTH:
                                    rfid = rfid_orig
                                elif len(rfid_orig) >= settings.LF_RFID_LENGTH:
                                    rfid = rfid_orig[:settings.LF_RFID_LENGTH]
                                rfid = ''.join(reversed(rfid)) if settings.LF_RFID_ORDER else ''.join(rfid)

                            tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
                            
                            tdiff = time.monotonic_ns() - self.lastTime[portNum]

                            if ps_sensor == '1':
                                if self.tmp_rfids[portNum] == rfid:
                                    continue

                                # if settings.RFID_DEBUG_ENABLE :
                                    # print(f'{tsr} {self.rfid_name} port_no {portNum+1} ps_sensor 1 : mode={self.access_mode[portNum]}, self.rfid=[{self.rfids[portNum]}], rfid=[{rfid}] ({tdiff})')
                                self.logger.info(f"{self.rfid_name} port_no {portNum+1} ps_sensor 1 : mode={self.access_mode[portNum]}, prev_rfid=[{self.prev_rfids[portNum]}], rfid=[{self.rfids[portNum]}], new_rfid=[{rfid}], tmp_rfid=[{self.tmp_rfids[portNum]}]")
                                
                                if not rfid: # ps_sensor=1, rfid=None
                                    # if self.rfids[portNum] == rfid: # ps_sensor=1, rfid=None, self.rfid=None
                                    #     self.logger.error(f"{self.rfid_name} A port_no {portNum+1} : ps sensor 1, place rfid is Null.")
                                    #     # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=128, subcode=1, msg_text='ps sensor 1, place rfid failed')
                                    #     # self.prev_rfids[portNum] = self.rfids[portNum]
                                    #     # self.rfids[portNum] = ''
                                    #     self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=1, msg_text='ps sensor 1, place rfid is Null', server=True)
                                    # else: # ps_sensor=1, rfid=None, self.rfid=xxxxxx
                                    if self.rfids[portNum] != '':
                                        self.logger.info(f"{self.rfid_name} B port_no {portNum+1} : ps sensor 1, remove rfid [{self.rfids[portNum]}]")
                                        # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 1, remove rfid', server=True)
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = ''
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 1, remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                    self.logger.error(f"{self.rfid_name} C port_no {portNum+1} : ps sensor 1, place rfid is Null.")
                                    # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=128, subcode=1, msg_text='ps sensor 1, place rfid failed', server=True)
                                    # self.rfids[portNum] = rfid
                                    # self.prev_rfids[portNum] = self.rfids[portNum]
                                    # self.rfids[portNum] = rfid
                                    self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=1, msg_text='ps sensor 1, place rfid is Null', server=True)
                                else: # ps_sensor=1, rfid=xxxxxx
                                    if self.rfids[portNum] != '':
                                        self.logger.info(f"{self.rfid_name} D port_no {portNum+1} : ps sensor 1, remove rfid [{self.rfids[portNum]}]")
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = ''
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 1, remove rfid [{self.prev_rfids[portNum]}]", server=True)

                                    if len(rfid) == settings.LF_RFID_LENGTH: # ps_sensor=1, rfid=xxxxxx, len=rfid_length
                                        # if self.rfids[portNum] == rfid: # ps_sensor=1, rfid=xxxxxx, len=rfid_length, rfid=self.rfid
                                        #     # self.logger.info(f"port_no {portNum+1} D")
                                        #     # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=0, subcode=1, msg_text='ps sensor 1, place rfid')
                                        #     pass
                                        # else: # ps_sensor=1, rfid=xxxxxx, len=rfid_length, rfid != self.rfid
                                        #     if self.rfids[portNum] != '':
                                        #         self.logger.info(f"{self.rfid_name} E port_no {portNum+1} : ps sensor 1, remove rfid [{self.rfids[portNum]}]")
                                        #         self.prev_rfids[portNum] = self.rfids[portNum]
                                        #         self.rfids[portNum] = ''
                                        #         self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 1, remove rfid [{self.prev_rfids[portNum]}]", server=True)

                                        if re.match(pattern, rfid):
                                            self.logger.info(f"{self.rfid_name} F port_no {portNum+1} : ps sensor 1, place rfid [{rfid}]")
                                            self.prev_rfids[portNum] = self.rfids[portNum]
                                            self.rfids[portNum] = rfid
                                            self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=1, msg_text=f"ps sensor 1, place rfid [{self.rfids[portNum]}]", server=True)
                                        else:
                                            self.logger.error(f"{self.rfid_name} E port_no {portNum+1} : ps sensor 1, place rfid [{rfid}] is incorrect")
                                            self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=1, msg_text=f"ps sensor 1, place rfid [{rfid}] is incorrect", server=True)
                                    else: # ps_sensor=1, rfid=xxxxxx, len=not rfid_length
                                        # if self.rfids[portNum] == rfid: # ps_sensor=1, rfid=xxxxxx, len=not rfid_length, rfid=self.rfid
                                        self.logger.error(f"{self.rfid_name} G port_no {portNum+1} : ps sensor 1, place rfid [{rfid}] length is not {settings.LF_RFID_LENGTH}")
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=2, msg_text=f"ps sensor 1, place rfid [{rfid}] length is not {settings.LF_RFID_LENGTH}", server=True)
                                        # else: # ps_sensor=1, rfid=xxxxxx, len=not rfid_length, rfid != self.rfid
                                        #     if self.rfids[portNum] != '':
                                        #         self.logger.info(f"{self.rfid_name} H port_no {portNum+1} : ps sensor 1, remove rfid [{self.rfids[portNum]}]")
                                        #         # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 1, remove rfid', server=True)
                                        #         self.prev_rfids[portNum] = self.rfids[portNum]
                                        #         self.rfids[portNum] = ''
                                        #         self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 1, remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                        #     self.logger.error(f"{self.rfid_name} I port_no {portNum+1} : ps sensor 1, place rfid [{rfid}] length is not {settings.LF_RFID_LENGTH}")
                                        #     # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=128, subcode=2, msg_text=f"ps sensor 1, rfid length is not {settings.LF_RFID_LENGTH}", server=True)
                                        #     # self.rfids[portNum] = rfid
                                        #     self.prev_rfids[portNum] = self.rfids[portNum]
                                        #     self.rfids[portNum] = ''
                                        #     self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=2, msg_text=f"ps sensor 1, place rfid [{rfid}] length is not {settings.LF_RFID_LENGTH}", server=True)
                                self.sensors[portNum] = ps_sensor
                                self.tmp_rfids[portNum] = rfid
                            
                            elif ps_sensor == '0':
                                
                                if self.sensors[portNum] == ps_sensor:
                                    # if self.rfids[portNum] != '':
                                    #     self.logger.info(f"{self.rfid_name} J port_no {portNum+1} : ps sensor 0, remove rfid [{self.rfids[portNum]}]")
                                    #     self.prev_rfids[portNum] = self.rfids[portNum]
                                    #     self.rfids[portNum] = ''
                                    #     self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 0, remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                    # self.tmp_rfids[portNum] = ''
                                    continue

                                else: #### self.sensors[portNum] == '1' and ps_sensor == '0'
                                    # if settings.RFID_DEBUG_ENABLE :
                                    #     print(f'{tsr} {self.rfid_name} port_no {portNum+1} ps_sensor 0 : mode={self.access_mode[portNum]}, self.rfid=[{self.rfids[portNum]}], rfid=[{rfid}] ({tdiff})')
                                    self.logger.info(f"{self.rfid_name} port_no {portNum+1} ps_sensor 0 : mode={self.access_mode[portNum]}, prev_rfid=[{self.prev_rfids[portNum]}], rfid=[{self.rfids[portNum]}], new_rfid=[{rfid}], tmp_rfid=[{self.tmp_rfids[portNum]}]")
                                    
                                    if self.rfids[portNum] != '':
                                        self.logger.info(f"{self.rfid_name} K port_no {portNum+1} : ps sensor 0, remove rfid [{self.rfids[portNum]}]")
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = ''
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 0, remove rfid [{self.prev_rfids[portNum]}]", server=True)

                                    # if not rfid: # rfid == ''
                                    #     if self.rfids[portNum] == rfid: # rfid == '' and self.rfids == ''
                                    #         self.logger.info(f"{self.rfid_name} K port_no {portNum+1}")
                                    #         # # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=0, subcode=0, msg_text='ps sensor 0, no rfid')
                                    #         # self.prev_rfids[portNum] = self.rfids[portNum]
                                    #         # self.rfids[portNum] = rfid
                                    #         # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 0, no rfid')
                                    #     else: # rfid == '' and self.rfids == xxxxxx
                                    #         self.logger.info(f"{self.rfid_name} L port_no {portNum+1} : ps sensor 0, remove rfid [{self.rfids[portNum]}]")
                                    #         # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 0, remove rfid', server=True)
                                    #         # self.rfids[portNum] = rfid
                                    #         self.prev_rfids[portNum] = self.rfids[portNum]
                                    #         self.rfids[portNum] = ''
                                    #         self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 0, remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                    # else: # rfid == xxxxxx
                                    #     if self.rfids[portNum] == '':
                                    #         self.logger.info(f"{self.rfid_name} M port_no {portNum+1}")
                                    #         # # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 0, no rfid')
                                    #         # self.prev_rfids[portNum] = self.rfids[portNum]
                                    #         # self.rfids[portNum] = rfid
                                    #         # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 0, no rfid')
                                    #     else:
                                    #         self.logger.info(f"{self.rfid_name} N port_no {portNum+1} : ps sensor 0, remove rfid [{self.rfids[portNum]}]")
                                    #         # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text='ps sensor 0, remove rfid', server=True)
                                    #         # self.rfids[portNum] = ''
                                    #         self.prev_rfids[portNum] = self.rfids[portNum]
                                    #         self.rfids[portNum] = ''
                                    #         self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"ps sensor 0, remove rfid [{self.prev_rfids[portNum]}]", server=True)

                                        # if len(rfid) == settings.LF_RFID_LENGTH:
                                        #     if self.rfids[portNum] == rfid:
                                        #         self.mqtt_publish(port_no=portNum+1, rfid_data=rfid, type=2, code=0, subcode=2, msg_text='ps sensor 0, read rfid')
                                        #     else:
                                        #         self.rfids[portNum] = rfid
                                        #         self.mqtt_publish(port_no=portNum+1, rfid_data=rfid, type=2, code=0, subcode=2, msg_text='ps sensor 0, read rfid', server=True)
                                        # else:
                                        #     if self.rfids[portNum] == rfid:
                                        #         self.logger.error(f"port_no {portNum+1} : ps sensor 0, rfid length is not {settings.LF_RFID_LENGTH} : {rfid}")
                                        #         self.mqtt_publish(port_no=portNum+1, rfid_data=rfid, type=2, code=128, subcode=3, msg_text=f"ps sensor 0, rfid length is not {settings.LF_RFID_LENGTH}")
                                        #     else:
                                        #         self.rfids[portNum] = rfid
                                        #         self.logger.error(f"port_no {portNum+1} : ps sensor 0, rfid length is not {settings.LF_RFID_LENGTH} : {rfid}")
                                        #         self.mqtt_publish(port_no=portNum+1, rfid_data=rfid, type=2, code=128, subcode=3, msg_text=f"ps sensor 0, rfid length is not {settings.LF_RFID_LENGTH}", server=True)
                                    self.sensors[portNum] = ps_sensor
                                    self.tmp_rfids[portNum] = ''

                            else: # ps_sensor != '0' and ps_sensor != '1'
                                if self.tmp_rfids[portNum] == rfid:
                                    continue
                                self.logger.error(f"{self.rfid_name} O port_no {portNum+1} : ps sensor {ps_sensor}, old_rfid={self.rfids[portNum]}, rfid={rfid}")
                                # self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=rfid, type=2, code=128, subcode=4, msg_text=f"port_no {portNum+1} : ps sensor {ps_sensor}, old_rfid={self.rfids[portNum]}, rfid={rfid}", server=True)
                                self.prev_rfids[portNum] = self.rfids[portNum]
                                self.rfids[portNum] = ''
                                self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=4, msg_text=f"port_no {portNum+1} : ps sensor {ps_sensor}, old_rfid={self.prev_rfids[portNum]}, rfid={rfid}", server=True)
                                self.sensors[portNum] = ps_sensor
                                self.tmp_rfids[portNum] = rfid

                            # time.sleep(1)
                            # if ps_sensor == '1' :
                            #     if settings.RFID_DEBUG_ENABLE :
                            #         print(f'{tsr} port_no {portNum+1} #### {rfid} #### {tdiff}')
                            #     if len(rfid) == settings.LF_RFID_LENGTH:
                            #         self.tmp_rfids[portNum].append(rfid)
                            #         self.count[portNum] += 1
                            #     else:
                            #         self.loggger.error(f"port_no {portNum+1} : rfid length is not {settings.LF_RFID_LENGTH} : {rfid}")
                            # else:
                            #     if settings.RFID_DEBUG_ENABLE :
                            #         print(f'{tsr} port_no {portNum+1} no carrier id')

                            # if tdiff >= settings.RFID_READ_PS_TIME*1000000:
                            #     if self.count[portNum] > 1:
                            #         if self.check_all_same(self.tmp_rfids[portNum]):
                            #             self.rfids[portNum] = self.tmp_rfids[portNum][0]
                            #             if settings.RFID_DEBUG_ENABLE :
                            #                 print(self.tmp_rfids[portNum])
                            #                 print(f"port_no {portNum+1} : rfid = {self.rfids[portNum]}")
                            #         else:
                            #             self.logger.warning(f"port_no {portNum+1} : Read different rfid : {self.tmp_rfids[portNum]}")
                            #     elif self.count[portNum] == 1:
                            #         self.logger.warning(f"port_no {portNum+1} : Only read one rfid : {self.tmp_rfids[portNum]}")
                            #     else:
                            #         self.rfids[portNum] = False
                            #         if settings.RFID_DEBUG_ENABLE :
                            #             print(f"port_no {portNum+1} : rfid = None")
                            #     self.lastTime[portNum] = time.monotonic_ns()
                            #     self.count[portNum] = 0
                            #     self.tmp_rfids[portNum] = []

                            # if not rfid:
                            #     print('no carrier id')
                            # else:
                            #     print(f'{rfid}')
                            # self.rfids[portNum] = rfid

                        else: # not settings.RFID_READ_PS_ENABLE
                            # tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
                            # print(f'#### {tsr} before read')
                            tmp_rfids = []
                            for i in range(self.trycount):
                                rfid_orig = ''
                                for page in range(settings.LF_RFID_READ_PAGE_NUMS):
                                    rfid_page = self.cmd_read(portNum+1, page+1)
                                    if type(rfid_page) == str:
                                        rfid_orig += rfid_page
                                tmp_rfids.append(rfid_orig)
                                sleep(settings.LF_RFID_READ_INTERVAL_TIME/1000.0)
                            
                            # print(tmp_rfids)
                            rfid_orig = self.get_most_common_rfid(tmp_rfids)
                            # print(f"rfid_orig={rfid_orig}")
                            # tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
                            # print(f'#### {tsr} after read {rfid_orig}')

                            if rfid_orig:
                                rfid = rfid_orig[:settings.LF_RFID_LENGTH]
                                rfid = ''.join(reversed(rfid)) if settings.LF_RFID_ORDER else ''.join(rfid)
                            else: # rfid == ''
                                rfid = rfid_orig
                            
                            # if not rfid_orig: # rfid_orig = False
                            #     rfid = rfid_orig
                            # elif len(rfid_orig) < settings.LF_RFID_LENGTH:
                            #     rfid = rfid_orig
                            # elif len(rfid_orig) >= settings.LF_RFID_LENGTH:
                            #     rfid = rfid_orig[:settings.LF_RFID_LENGTH]
                            # else:
                            #     self.logger.error(f"{self.rfid_name} port_no {portNum+1} : rfid orig length error.")

                            # # if not rfid_orig: # rfid_orig = False
                            # if type(rfid_orig) != str:
                            #     rfid_orig = ''
                            
                            # if len(rfid_orig) == 0:
                            #     rfid = rfid_orig
                            # else:
                            #     if len(rfid_orig) < settings.LF_RFID_LENGTH:
                            #         rfid = rfid_orig
                            #     elif len(rfid_orig) >= settings.LF_RFID_LENGTH:
                            #         rfid = rfid_orig[:settings.LF_RFID_LENGTH]
                            #     rfid = ''.join(reversed(rfid)) if settings.LF_RFID_ORDER else ''.join(rfid)

                            tsr = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]

                            tdiff = time.monotonic_ns() - self.lastTime[portNum]

                            if self.tmp_rfids[portNum] != rfid:
                                # if settings.RFID_DEBUG_ENABLE :
                                #     print(f'{tsr} {self.rfid_name} port_no {portNum+1} : mode={self.access_mode[portNum]}, self.rfid=[{self.rfids[portNum]}], rfid=[{rfid}] ({tdiff})')
                                self.logger.info(f"{self.rfid_name} port_no {portNum+1} : mode={self.access_mode[portNum]}, prev_rfid=[{self.prev_rfids[portNum]}], rfid=[{self.rfids[portNum]}], new_rfid=[{rfid}], tmp_rfid=[{self.tmp_rfids[portNum]}]")
                                
                                if len(self.rfids[portNum]) == 0 and len(rfid) > 0:
                                    if re.match(pattern, rfid):
                                        self.logger.info(f"{self.rfid_name} P port_no {portNum+1} : place rfid [{rfid}]")
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = rfid
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=1, msg_text=f"place rfid [{self.rfids[portNum]}]", server=True)
                                    else:
                                        self.logger.error(f"{self.rfid_name} Q port_no {portNum+1} : place rfid [{rfid}] is incorrect")
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=1, msg_text=f"place rfid [{rfid}] is incorrect", server=True)
                                elif len(self.rfids[portNum]) > 0 and len(rfid) == 0:
                                    self.logger.info(f"{self.rfid_name} R port_no {portNum+1} : remove rfid [{self.rfids[portNum]}]")
                                    self.prev_rfids[portNum] = self.rfids[portNum]
                                    self.rfids[portNum] = rfid
                                    self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                else:
                                    if re.match(pattern, rfid):
                                        self.logger.info(f"{self.rfid_name} S port_no {portNum+1} : remove rfid [{self.rfids[portNum]}]")
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = ''
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=0, msg_text=f"remove rfid [{self.prev_rfids[portNum]}]", server=True)
                                        
                                        self.logger.info(f"{self.rfid_name} T port_no {portNum+1} : place rfid [{rfid}]")
                                        self.prev_rfids[portNum] = self.rfids[portNum]
                                        self.rfids[portNum] = rfid
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=0, subcode=1, msg_text=f"place rfid [{self.rfids[portNum]}]", server=True)
                                    else:
                                        self.logger.error(f"{self.rfid_name} U port_no {portNum+1} : place rfid [{rfid}] is incorrect")
                                        self.mqtt_publish(port_no=portNum+1, prev_rfid_data=self.prev_rfids[portNum], rfid_data=self.rfids[portNum], type=2, code=128, subcode=1, msg_text=f"place rfid [{rfid}] is incorrect", server=True)
                                self.tmp_rfids[portNum] = rfid

                        #print(portNum+1, rfid, ps)
                        # time.sleep(1)
                    if self.reconnect:
                        self.reconnect = False
                        self.send_event(True, 128, 2, 'reconnect device')
                        self.logger.warning(f"{self.rfid_name} reconnect device")
                        self.dev_rs485.close()
                        self.dev_rs485 = None
                        self.send_event(True, 0, 1, 'close')
                        time.sleep(10)

                    time.sleep(0.5)
                    # self.cmd_beep()
                except Exception as err:
                    self.logger.error(f"{self.rfid_name} SunionPS error={str(err)}")
                    self.send_event(True, 128, 1, 'could not open port')
                    time.sleep(10)

if __name__ == '__main__':
    #sun1 = Sunion('/dev/ttyAMA0', 4)
    # sun1 = Sunion('/dev/ttyUSB1', 4)
    sun1 = Sunion('COM9', 4)
    sun1.daemon = True
    sun1.start()
    while True:
        for num in range(sun1.portNumber):
            print(num+1, sun1.rfids[num], sun1.sensors[num])

        print('-'*20)
        time.sleep(1)
