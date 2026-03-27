import time
from time import sleep
import serial
import struct
import schedule
import threading
import traceback
import collections
# from e84_err_code import e84_err_code
from datetime import datetime, timedelta
import json

from config import settings
# from global_log import console_logger
from global_log import Logger
# from global_variables import ftp_alarmlist
from global_variables import alarm_code
import sys
#from config import e84_errorCode
from collections import OrderedDict
import queue
import asyncio
from e84_client import E84Client

#e84Path = '/dev/ttyS5'
#e84Path = '/dev/ttyUSB0'

# set
manual = (0x55, 0xAA, 0x80, 0x03, 0x00, 0x00)
manual2 = (0x55, 0xAA, 0x80, 0x03, 0x01, 0x00)
auto = (0x55, 0xAA, 0x80, 0x03, 0x00, 0x01)
auto2 = (0x55, 0xAA, 0x80, 0x03, 0x01, 0x01)
reset = (0x55, 0xAA, 0x80, 0x02, 0x00, 0x00)
reset2 = (0x55, 0xAA, 0x80, 0x02, 0x00, 0x01)
ps_on = (0x55, 0xAA, 0x80, 0x19, 0x00, 0xFF)
ps_off = (0x55, 0xAA, 0x80, 0x19, 0x00, 0x00)
clamp_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x03)
clamp_off = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x01)
relay_on = (0x55, 0xAA, 0x81, 0x25, 0x00, 0x01)
relay_off = (0x55, 0xAA, 0x81, 0x25, 0x00, 0x00)
inch12_on = (0x55, 0xAA, 0x81, 0x43, 0x00, 0x01)
inch12_off = (0x55, 0xAA, 0x81, 0x43, 0x00, 0x00)
sensor_HRDD_FRSC = (0x55, 0xAA, 0x01, 0x18, 0x00, 0x00)
light_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x05)
eqer_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x09)
check_light_on = (0x55, 0xAA, 0x81, 0x23, 0x00, 0x01)
check_light_off = (0x55, 0xAA, 0x81, 0x23, 0x00, 0x00)
es_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x01)
es_off = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x00)
enable0070 = (0x55, 0xAA, 0x80, 0x13, 0x55, 0xAA)

            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x03)) # simulation mode clamp on
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x01)) # simulation mode clamp off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x00)) # simulation mode ps off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x01)) # simulation mode ps on


link = (0x55, 0xAA, 0x00, 0x52, 0x00, 0x00)
version = (0x55, 0xAA, 0x00, 0x00, 0x01, 0x00)
product_code = (0x55, 0xAA, 0x00, 0x0f, 0x00, 0x01)


test2 = (0x55, 0xAA, 0x00, 0x57, 0x00, 0x00) # 87 eapport_0.OLD_PSPL = eapport_0.PSPL
                                                # 設定為雙 PORT 時，取得 sensor 狀態（0:Off 1:ON 3:NO Ready 4:NO Set）
                                                # CS0=ON 時 Left PORT Sensor 狀態（PS = bit0~3 ； PL = bit4~7）
                                                # CS1=ON 時 Right PORT Sensor 狀態（PS = bit8~11；PL= bit12~15）

# cmd=0x10, 16
# cmd=0x11, 17
# cmd=0x12, 18
# cmd=0x19, 25
# cmd=0x1C, 28
# cmd=0x16, 22
# cmd=0x104, 260
# cmd=0x118, 280
# cmd=0x11B, 283
# cmd=0x8052, 32850

# read
e84_out =     (0x55, 0xAA, 0x00, 0x10, 0x00, 0x00) # 16 oureg_en
e84_in =      (0x55, 0xAA, 0x00, 0x11, 0x00, 0x00) # 17 inreg_en
e84_smg =  (0x55, 0xAA, 0x00, 0x12, 0x00, 0x00) # 18 goreg
pspl =        (0x55, 0xAA, 0x00, 0x19, 0x00, 0x00) # 25 LED_PSPL  # Gyro-E84 PL
                                    # this.eapport_0.LED_PSPL[int_5] = int_7;
                                    # int int_9 = (this.eapport_0.LED_PSPL[int_5] & 31) | (this.eapport_0.LED_DONE[int_5] & 3) << 6 | (this.eapport_0.LED_EXTIO[int_5] & 16) << 3;
                                    # this.method_9(int_5, 2, int_9);
pspl2 =        (0x55, 0xAA, 0x01, 0x04, 0x00, 0x00) # Gyro-E84 PS
relay =        (0x55, 0xAA, 0x01, 0x25, 0x00, 0x00) # Gyro-E84 RELAY
mode_state = (0x55, 0xAA, 0x00, 0x1C, 0x00, 0x00) # 28 modereg seems like related to 25
                                    # if (this.loadport_0[int_5].modereg != int_7)
                                    # {
                                    #     this.loadport_0[int_5].modereg = int_7;
                                    #     this.method_9(int_5, 3, this.loadport_0[int_5].modereg);
                                    # }
sensor_elce =  (0x55, 0xAA, 0x00, 0x16, 0x00, 0x00) # 22 cl_en
test3 = (0x55, 0xAA, 0x01, 0x04, 0x00, 0x00) # 260 
                                    # this.eapport_0.LED_DONE[int_5] = int_7;
                                    # int int_9 = (this.eapport_0.LED_PSPL[int_5] & 31) | (this.eapport_0.LED_DONE[int_5] & 3) << 6 | (this.eapport_0.LED_EXTIO[int_5] & 16) << 3;
                                    # this.method_9(int_5, 2, int_9);
test4 = (0x55, 0xAA, 0x01, 0x18, 0x00, 0x00) # 280 
									# this.eapport_0.LED_EXTIO[int_5] = int_7;
									# int int_9 = (this.eapport_0.LED_PSPL[int_5] & 31) | (this.eapport_0.LED_DONE[int_5] & 3) << 6 | (this.eapport_0.LED_EXTIO[int_5] & 16) << 3;
									# this.method_9(int_5, 2, int_9);
test5 = (0x55, 0xAA, 0x01, 0x1B, 0x00, 0x00) # 283
link_reset = (0x55, 0xAA, 0x80, 0x52, 0x00, 0x00) # 32850 RS232 Link 異常時(link timer reset)

mode =          (0x55, 0xAA, 0x00, 0x03, 0x00, 0x00)

sensor_use =    (0x55, 0xAA, 0x00, 0x1A, 0x00, 0x00) # 
sensor_set =    (0x55, 0xAA, 0x00, 0x1B, 0x00, 0x00)
last_error =    (0x55, 0xAA, 0x00, 0x49, 0x00, 0x00)

def tp1(timeout):
    return (0x55, 0xAA, 0x80, 0x40, timeout//256, timeout%256)
def tp2(timeout):
    return (0x55, 0xAA, 0x80, 0x41, timeout//256, timeout%256)
def tp3(timeout):
    return (0x55, 0xAA, 0x80, 0x42, timeout//256, timeout%256)
def tp4(timeout):
    return (0x55, 0xAA, 0x80, 0x43, timeout//256, timeout%256)
def tp5(timeout):
    return (0x55, 0xAA, 0x80, 0x44, timeout//256, timeout%256)

class E84(threading.Thread):
    def __init__(self, devPath, controller=None, log=None, enable=True, port_no=1, port_id='LP1', rfid=None, rfid2=None, event_mgr=None, led_id=1, max_queue_size=1000):
        threading.Thread.__init__(self)
        self.controller = controller
        self.devPath = devPath
        self.state = {'cont':False, 'compt':False, 'busy':False, 'tr_req':False, 'am_avbl':False, 'cs_1':False, 'cs_0':False, 'valid':False,
                'es':False, 'ho_avbl':False, 'vs_1':False, 'vs_0':False, 'ready':False, 'va':False, 'u_req':False, 'l_req':False, 
                'go':False, 'power':False, 'manual':False, 'auto':False, 'load':False, 'unload':False, 'eq_er':False, 'clamp':False, 
                'light':False, 'alarm':True, 'ps':False, 
                'start_to_load':False, 'start_to_unload':False,
                'unloading':False, 'loading':False, 'load_complete':False, 'unload_complete':False}
        self.led = {
            'cont':False, 'compt':False, 'busy':False, 'tr_req':False, 'am_avbl':False, 'cs_1':False, 'cs_0':False, 'valid':False,
            'es':False, 'ho_avbl':False, 'vs_1':False, 'vs_0':False, 'ready':False, 'va':False, 'u_req':False, 'l_req':False,
            'power':False, 'go':False
        }
        self.gpio1 = {
            'go':False, 'mode':False, 'select':False
        }
        self.gpio2 = {
            'es':False, 'clamp':False, 'light':False, 'eq_er':False
        }
        self.sensor_HRDD_FRSC = {
            'home':False, 'ready':False, 'door_close':False, 'door_open':False, 'finish':False, 'run':False, 'standby':False, 'carrier':False
        }
        self.e84_dual = 0
        self.fw_version = ''
        self.errorCode = 0
        self.errorMsg = ''
        # self.pspl = False
        self.stop = False
        self.enable = enable
        self.restart = False
        self.daily_reconnect = False
        self.daily_reconnect_time = datetime.now()
        # self.e84_queue = collections.deque()
        self.response_queue = collections.deque()
        self.props_queue = collections.deque()
        self.e84_timeout = 30
        self.lastTime = time.time()
        self.count = 0
        self.e84 = None
        self.logger = Logger("e84_{}".format(port_id), "e84_{}.log".format(port_id))

        self.rfid = rfid
        self.rfid2 = rfid2
        self.event_mgr = event_mgr

        self.power = 0
        self.load_function = 0

        # self.port_id = port_id
        # self.port_id2 = None
        self.port_id = [port_id, '', '']
        self.message = ''
        # self.port_no = port_no
        # self.port_no2 = -1
        self.port_no = [port_no, -1, -1]
        self.mode_bit = 0
        # self.mode = 0
        # self.mode2 = 0
        self.mode = [0]*3
        # self.port_status = 0
        # self.port_status2 = 0
        self.port_status = [0]*3
        self.safety = -1
        self.pspl = -1
        self.pspl2 = -1
        self.relay = -1
        self.dual = 0
        # self.load = -1
        # self.load2 = -1
        self.load = [-1]*3
        self.cs = -1
        # PortState : 
        # 0=Out of service (Disable) 
        # 1=Transfer blocked (Include wait, check, run) 
        # 2=Near completion
        # 3=Ready to unload 
        # 4=Empty (Ready to load) 
        # 5=Reject and ready to unload
        # 6=PortAlarm
        
        # New PortState : 
        # 0=Out of service (Disable) 
        # 1=Ready to Load 
        # 2=Ready to Unload
        # 3=Loading 
        # 4=Unloading 
        # 5=Load Complete
        # 6=Unload Complete
        # 128, 0x80=Port Alarm
        # 255, 0xFF=Unknown Command
        # self.port_status_msg = 'Out of Service'
        # self.port_status_msg2 = 'Out of Service'
        self.port_status_msg = ['Out of Service']*3
        self.port_connected = 0
        
        self.sensor_elce = -1
        self.sensor_hrdd_frsc = -1
        self.pspl_usage = -1
        self.pspl_setting = -1
        self.e84_out = -1
        self.e84_in = -1
        self.e84_smg = -1

        # self.alarm_id = 0
        # self.alarm_id2 = 0
        self.alarm_id = [0]*3
        # self.alarm_text = ''
        # self.alarm_text2 = ''
        self.alarm_text = ['']*3

        self.rfid_type = 0
        self.rfid_port = 0
        self.rfid_dual = 0
        self.rfid_page = 1
        # self.rfid_data = None
        # self.rfid_data2 = None
        self.rfid_data = ['']*3
        self.prev_rfid_data = ['']*3
        self.rfid_length = [settings.RFID_CS0_LENGTH, settings.RFID_CS1_LENGTH]
        self.rfid_order = [settings.RFID_CS0_ORDER, settings.RFID_CS1_ORDER]
        self.rfid_pattern = [settings.RFID_CS0_PATTERN, settings.RFID_CS1_PATTERN]
        self.clamp = False
        self.led_id = led_id
        self.incoming_queue = queue.Queue(maxsize=max_queue_size)

        '''
        try:
            self.e84 = serial.Serial(self.devPath, 115200, 8, 'N', 1, timeout=0.25)
        except:
            print('{} not open'.format(self.devPath))'''

        try:
            # self.e84 = E84Client(self.devPath, f"COM{settings.E84_RF_SENSOR_COM}", baudrate=115200, on_sensor_event=self.quick_monitor, on_alarm_event=self.on_alarm, event_queue_size=100)
            # asyncio.run(self.init_e84())
            # asyncio.run(self.open_RF_channel())
            self._run_coro(self.init_e84())
            # self._run_coro(self.open_RF_channel())
            # self.e84 = E84Client(self.devPath, baudrate=115200, on_sensor_event=self.quick_monitor, on_alarm_event=self.on_alarm, event_queue_size=100)
            # self.e84.connect_async()

            # handler_task = asyncio.create_task(self.complex_event_handler())

            # success = self.e84.initialize_device()
            # print(f"Load 結果: {'成功' if success else '失敗'}")
        except Exception as err:
            print(str(err))

    async def init_e84(self):
        try:
            self.e84 = E84Client(self.devPath, f"COM{settings.E84_RF_SENSOR_COM}", baudrate=115200, on_message_event=self.e84_message, on_sensor_event=self.quick_monitor, on_alarm_event=self.on_alarm, event_queue_size=1000, glogger=self.logger)
            await self.e84.connect_async()

            # self.handler_task = asyncio.create_task(self.complex_event_handler())
            # Run handler in a resilient runner that restarts on unexpected exceptions
            self.handler_task = asyncio.create_task(self._task_runner(self.complex_event_handler, "complex_event_handler"))
            success = await self.e84.initialize_device()
            print("=" * 30 + f" E84 Initialize 結果: {'成功' if success else '失敗'} " + "=" * 30)

        except Exception as err:
            # print(str(err))
            self.logger.error(f"init_e84 failed: {err}\n{traceback.format_exc()}")
        finally:
            if self.e84._state.value == "connected":
                await self.e84.disconnect_async()

    # Callback for E84 message
    def e84_message(self, data: str):
        print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [即時 E84 message] {data.hex()}")
        try:
            self.incoming_queue.put_nowait(data)
        except queue.Full:
            self.logger.info(f"{self.port_id} {self.port} serial port incoming queue full, dropping valid frame: {data.hex()}")

    def read(self, block=True, timeout=None):
        """Read a line from incoming queue."""
        try:
            data = self.incoming_queue.get(block=block, timeout=timeout)
            # self.logger.info(f"###### read : {bytes(data).hex()}")
            return data
        except queue.Empty:
            return None

    # Callback 用於即時監控
    def quick_monitor(self, signal: str, state: bool):
        print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [即時] {signal}: {'ON' if state else 'OFF'}")

    # 複雜的事件處理邏輯
    async def complex_event_handler(self):
        """複雜的事件處理邏輯"""
        l_req_count = 0
        # while True:
        #     try:
        #         # get_event is async — await it; handle timeout and None defensively
        #         event = await self.e84.get_event(timeout=1.0)
        #         if event is None:
        #             continue
        #         print(f"****************************** [即時] {event.signal_name}: {event.description}")
        #         # 複雜的狀態機處理
        #         if event.signal_name == "L_REQ":
        #             l_req_count += 1
        #             print(f"[分析] L_REQ 觸發次數: {l_req_count}")
                
        #         # 其他複雜邏輯...
                
        #     except asyncio.TimeoutError:
        #         continue
        while True:
            try:
                event = await self.e84.get_event(timeout=1.0)
                if event is None:
                    continue
                print(f"****************************** [即時] {event.signal_name}: {event.description}")
                if event.signal_name == "L_REQ":
                    l_req_count += 1
                    print(f"[分析] L_REQ 觸發次數: {l_req_count}")
                # other complex logic...
            except asyncio.TimeoutError:
                continue
            except Exception as err:
                # Log and continue rather than letting the coroutine die
                self.logger.error(f"****************************** complex_event_handler error: {err}\n{traceback.format_exc()}")
                await asyncio.sleep(0.5)
                continue

    # Define alarm callback
    def on_alarm(self, alarm_type: str, alarm_code: int, description: str):
        print(f"⚠️ Alarm: {description}")
        if alarm_type == "offline":
            # Handle device offline
            print("設備離線，檢查連線")
        elif alarm_type == "ta_timeout":
            # Handle TA timeout
            ta_num = (alarm_code & 0x00FF) + 1
            print(f"TA{ta_num} 超時，檢查參數設定")


    def mqtt_publish_response(self, cmd, res=None, correlation=None):
        data = OrderedDict()
        data['port_id'] = self.port_id[0]
        data['port_no'] = self.port_no[0]
        data['cmd'] = cmd
        data['result'] = res
        data['correlation'] = correlation
        data['occurred_at'] = time.time()
        self.event_mgr.on_notify(data)

    def mqtt_publish(self, type, code, subcode=-1, msg_text=None):
        data = OrderedDict()
        data['Server'] = True
        data['device_id'] = self.controller.device_id
        data['port_id'] = self.port_id[0]
        data['port_no'] = self.port_no[0]
        data['dual_port'] = 0
        data['mode'] = self.mode[0]
        data['eqp_state'] = self.controller.equipment_state
        data['prev_carrier_id'] = self.prev_rfid_data[0]
        data['carrier_id'] = self.rfid_data[0]
        data['type'] = type
        data['stream'] = -1
        data['function'] = -1
        data['code_id'] = code
        data['sub_id'] = subcode
        data['msg_text'] = msg_text
        data['status'] = ''
        data['occurred_at'] = time.time()
        self.event_mgr.on_notify(data)

    ######### test alarm used
    def send_alarm(self, subcode='', set=1, cs=0):
        # try:
        #     data = {}
        #     status = {}
        #     status['alarm_id'] = subcode
        #     status['alarm_text'] = self.alarm_text = ftp_alarmlist['S05F01'][128][subcode]['msgtext']
        # except Exception as err:
        #     status['alarm_id'] = subcode
        #     status['alarm_text'] = '------'
        try: 
            data = OrderedDict()
            
            # self.alarm_text2 = ftp_alarmlist['S05F01'][128][subcode]['msgtext']
            alarm_text = self.alarm_msg(subcode, cs)
            
            data['Server'] = True
            data['device_id'] = self.controller.device_id
            data['port_no'] = self.port_no[cs]
            data['port_id'] = self.port_id[cs]
            data['port_state'] = self.port_status[cs]
            data['eqp_state'] = self.controller.equipment_state
            data['prev_carrier_id'] = self.prev_rfid_data[cs]
            data['carrier_id'] = self.rfid_data[cs]
            data['dual_port'] = cs
            data['mode'] = self.mode[cs] # Access Mode 0: Unknown, 1: Auto, 2: Manual
            data['load'] = self.load[cs] #  0071 status
            data['alarm_id'] = int(subcode, 16)
            data['alarm_text'] = alarm_text
            data['type'] = 0
            data['stream'] = -1
            data['function'] = -1
            data['code_id'] = 128
            data['sub_id'] = int(subcode, 16)
            data['msg_text'] = alarm_text
            data['status'] = set
            data['occurred_at'] = time.time()
            # data['version'] = f"{self.fw_version}, {settings.SW_VERSION}"
            data['version'] = f"{self.fw_version}"
            self.event_mgr.on_notify(data)
            
        except Exception as err:
            self.logger.info(str(err))

    # do not support status compare with send_event
    def send_event2(self, server=False, type=0, stream=-1, function=-1, code=-1, subcode=-1, msg_text=None, cs=0):
        try:
            data = OrderedDict()
            
            if server:
                data['Server'] = True

            status = OrderedDict()
            status['P'] = self.pspl # PSPL
            if settings.E84_TYPE == 1:
                status['S'] = self.pspl2 # PSPL
                status['R'] = self.relay # RELAY
            status['I'] = self.e84_in       # E84 Input
            status['O'] = self.e84_out      # E84 output
            status['G'] = self.e84_smg      # Select, Mode, GO
            status['E'] = self.sensor_elce  # EQ_ER, Light, CLAMP, ES
                
            data['device_id'] = self.controller.device_id
            data['port_no'] = self.port_no[cs]
            data['port_id'] = self.port_id[cs]
            data['port_state'] = self.port_status[cs]
            data['eqp_state'] = self.controller.equipment_state
            data['prev_carrier_id'] = self.prev_rfid_data[cs]
            data['carrier_id'] = self.rfid_data[cs]
            data['dual_port'] = cs
            data['mode'] = self.mode[cs] # Access Mode 0: Unknown, 1: Auto, 2: Manual
            data['load'] = self.load[cs]  # 0071 status
            data['alarm_id'] = self.alarm_id[cs]
            data['alarm_text'] = self.alarm_text[cs]
            data['type'] = type
            data['stream'] = stream
            data['function'] = function
            data['code_id'] = code
            data['sub_id'] = subcode
            data['msg_text'] = msg_text
            data['status'] = json.dumps(status)
            data['occurred_at'] = time.time()
            # data['version'] = f"{self.fw_version}, {settings.SW_VERSION}"
            data['version'] = f"{self.fw_version}"
            self.event_mgr.on_notify(data)
        except Exception as err:
            self.logger.info(str(err))

    # support status
    def send_event(self, server=False, code=0, subcode=-1, msg_text=None, cs=0):
        try:
            # self.rfid_type = 0
            # self.rfid_port = 0
            # self.rfid_dual = 0
            # self.rfid_page = 1
            # self.rfid_data = None
            
            # rfid = {}
            # if not (self.rfid == None):
            #     rfid['T'] = self.rfid.type
            #     rfid['G'] = self.rfid.page_num
            # rfid['P'] = self.port_no
            # rfid['V'] = self.rfid_data
            # status['R'] = json.dumps(rfid) # RFID
            
            status = OrderedDict()
            status['P'] = self.pspl # PSPL
            if settings.E84_TYPE == 1:
                status['S'] = self.pspl2 # PSPL
                status['R'] = self.relay # RELAY
            status['I'] = self.e84_in       # E84 Input
            status['O'] = self.e84_out      # E84 output
            status['G'] = self.e84_smg      # Select, Mode, GO
            status['E'] = self.sensor_elce  # EQ_ER, Light, CLAMP, ES

            data = OrderedDict()

            if server:
                data['Server'] = True
            data['device_id'] = self.controller.device_id
            data['port_no'] = self.port_no[cs]
            data['port_id'] = self.port_id[cs]
            data['port_state'] = self.port_status[cs]
            data['eqp_state'] = self.controller.equipment_state
            data['prev_carrier_id'] = self.prev_rfid_data[cs]
            data['carrier_id'] = self.rfid_data[cs]
            data['dual_port'] = cs
            data['mode'] = self.mode[cs] # Access Mode 0: Unknown, 1: Auto, 2: Manual
            data['load'] = self.load[cs]  # 0071 status
            data['alarm_id'] = self.alarm_id[cs]
            data['alarm_text'] = self.alarm_text[cs]
            data['type'] = 0
            data['stream'] = -1
            data['function'] = -1
            data['code_id'] = code
            data['sub_id'] = subcode
            data['msg_text'] = msg_text
            data['status'] = json.dumps(status)
            data['occurred_at'] = time.time()
            # data['version'] = f"{self.fw_version}, {settings.SW_VERSION}"
            data['version'] = f"{self.fw_version}"
            self.event_mgr.on_notify(data)

        except Exception as err:
            self.logger.info(str(err))

    def mqtt_publish_secsgem(self, stream, function, ceid, rptid, status=None, message=None):
        data = OrderedDict()
        data['stream'] = stream
        data['function'] = function
        data['ceid'] = ceid
        data['rptid'] = rptid

        data['portid'] = self.port_id[0]
        data['status'] = status
        data['message'] = message
        data['occurred_at'] = time.time()
        self.event_mgr.on_notify(data)

    def e84_cmd(self, data, high=False):
        # SmartIO-AGV comment out
        return

        if self.e84 == None:
            return
            
        data = list(data)
        data.append(sum(data)%256)
        # self.e84_queue.append(struct.pack('>BBBBBBB', *data))
        # #e84.write(struct.pack('>BBBBBBB', *data))
        self.e84.write(struct.pack('>BBBBBBB', *data), high)
        # self.e84.send_and_wait(cmd=struct.pack('>BBBBBBB', *data))

    def run_cmd2(self, cs, cmd, data):
        
        if self.e84 == None:
            return
        
        cmd2 = '55aa' + cmd + data
        cmd3 = bytes.fromhex(cmd2)
        # print(list(cmd3))
        # print(hex(int(cmd2, 16)))
        print(f"cmd=0x{int(cmd, 16):04X}, data=0x{int(data, 16):04X}")
        
        self.e84_cmd(cmd3, True)

    # def check(self):
    #     self.count += 1
    #     self.logger.info(f"{self.port_id[0]} E84 disconnected {self.count}")
        
    #     if self.count > 15:
    #         # self.state['alarm'] = True
    #         self.errorCode = 9999
    #         self.errorMsg = 'e84 disconnected'
    #         self.port_connected = 9999
    #         # self.port_status = 6
    #         # self.alarm_id = 9999
    #         # self.alarm_text = 'e84 disconnected'
    #         self.send_event(True, int('0090', 16), self.port_connected, 'E84 disconnected')
    #         self.logger.info(f"{self.port_id[0]} E84 disconnected {self.count}")
    #         ## 0 : E84, 1 : E87, 2 : LF-RFID, 3 : UHF-RFID
    #         # self.mqtt_publish(self.errorCode, 0, 'E84 disconnected')
    #     time.sleep(1)

    def connect_serial_port(self):
        return
        try:
            if self.e84 != None:
                self.e84.stop()
                time.sleep(3)
                self.e84 = None
                self.logger.info(f"{self.port_id[0]} disconnect COM port")

            # self.e84 = serial.Serial(self.devPath, 115200, 8, 'N', 1, timeout=0.25)
            # # self.e84.flushInput()
            # self.e84.reset_input_buffer()
            # self.logger.info(f"{self.port_id[0]} connect COM port")
            # self.e84_cmd(initial)
            # # self.e84_cmd(read_mode)

            self.e84 = SerialPortHandler(port=self.devPath, port_id=self.port_id[0], logger=self.logger)
            self.e84.start()
            self.logger.info(f"{self.port_id[0]} connect COM port")
            # self.e84_cmd(initial)

        except Exception as err:
            self.logger.info(str(err))
            self.e84 = None
            time.sleep(1)

    def enable_port(self, enable):
        if enable:
            self.enable = True
        else:
            self.enable = False

    def disconnect_serial_port(self):
        return
        try:
            if self.e84 != None:
                self.e84.stop()
                time.sleep(3)
                self.e84 = None
                self.logger.info(f"{self.port_id[0]} disconnect COM port")
        except Exception as err:
            self.logger.info(str(err))
            self.e84 = None

    def check_connection(self):
        if not self.enable:
            return
        # self.e84_cmd(version)
        self.e84_cmd(product_code)
        pass

    def update_rfid_data(self):
        
        if self.e84 == None:
            return
        
        if self.rfid == None:
            return
        
        if not self.enable:
            return
        
        try:
            if self.rfid.dev_rs485 == None:
                # self.mqtt_publish(5, -1, "")
                pass
            else:
                sub = -1
                if self.rfid.type == 'LF':
                    sub = 1
                    # self.mqtt_publish(5, 0, self.rfid.cmd_read(self.port_no+1))
                elif 'UHF' in self.rfid.type:
                    sub = 2
                    # self.mqtt_publish(5, 1, self.rfid.cmd_read(self.port_no+1))
                else:
                    self.logger.info('RFID type error')
                # self.mqtt_publish(5, 'rfid', self.rfid.cmd_read(self.port_no+1))
                    
                if sub < 0:
                    return
                
                sn = ''
                # sn = self.rfid.cmd_read(self.port_no+1)
                sn = self.rfid.rfids[self.port_no[0]-1]

                # self.mqtt_publish(2, sub, 0, 'RFID change')
                
                if self.rfid_data[0] == None or self.rfid_data[0] != sn:
                    # self.logger.info(self.port_id, ' rfid_data : ', sn)
                    self.rfid_data[0] = sn
                    # self.mqtt_publish(2, sub, 0, 'RFID change')
                    
                if self.dual > 0:
                    for m in range(1, self.dual+1):
                        # sn = self.rfid.rfids[self.port_no2-1]
                        sn = self.rfid.rfids[self.port_no[m]-1]
                    
                        if self.rfid_data[m] == None or self.rfid_data[m] != sn:
                            # self.logger.info(self.port_no2, ' rfid_data2 : ', sn)
                            self.rfid_data[m] = sn
                    

        except Exception as err :
            self.logger.info(str(err))
    
    def clamp_test(self):
        if not self.enable:
            return
        
        if self.clamp:
            self.e84_cmd(clamp_off)
            self.clamp = False
        else:
            self.e84_cmd(clamp_on)
            self.clamp = True
    
    def memory_check(self):
        if not self.enable:
            return
        
        try:
            e84_queue_size = len(self.e84_queue)
            input_buffer_size = 0
            output_buffer_size = 0
            if self.e84 :
                input_buffer_size = self.e84.in_waiting
                output_buffer_size = self.e84.out_waiting
            
            stdout_size = sys.getsizeof(sys.stdout)
                
            self.logger.info(f"e84_svc {self.port_id[0]} : input size = {input_buffer_size}, output size = {output_buffer_size}, queue_size = {e84_queue_size}, stdout = {stdout_size}")
            # self.logger.info(f"{self.port_id} : stdout = {stdout_size}, logger size = {sys.getsizeof(self.logger)}, logger file = {self.logger.getfilestreamsize()}, logger stream = {self.logger.getstdoutstreamsize()}, logger sql = {self.logger.getsqlstreamsize()}")
        except Exception as err:
            self.logger.info(str(err))
    
    def update_state(self):
        
        if not self.enable:
            return
        
        if self.e84:
            if not self.e84.is_connected():
                return

        # self.e84_cmd(last_error)
        # self.e84_cmd(link) # don't get any response
        # self.e84_cmd(test2)

        # self.e84_cmd(version)   # check e84 is connecting
        self.e84_cmd(e84_out) 
        self.e84_cmd(e84_in)
        self.e84_cmd(e84_smg) # GO Mode Select
        self.e84_cmd(pspl)
        if settings.E84_TYPE == 1:
            self.e84_cmd(pspl2)
            self.e84_cmd(relay)
        # self.e84_cmd(mode_state)
        self.e84_cmd(sensor_elce) # ES CLAMP Light Curtain EQ_ER
        self.e84_cmd(test3)
        self.e84_cmd(test4)
        self.e84_cmd(test5)
        # self.e84_cmd(link_reset)

        # self.e84_cmd(sensor_use)
        # self.e84_cmd(sensor_set)
        # self.e84_cmd(mode)
        
    def send_status(self):
        for m in range(self.dual+1):
            self.send_event2(server=True, stream=6, function=11, code=0, subcode=0, msg_text=self.port_status_msg[m], cs=m)

    def send_status_ledboard(self):
        for m in range(self.dual+1):
            self.send_event2(server=False, type=4, stream=6, function=11, code=0, subcode=0, msg_text=self.port_status_msg[m], cs=m)

    def api_request(self, cmd, data, props):
        
        if self.e84 == None:
            return
        req = OrderedDict()
        req['cmd'] = cmd
        req['props'] = props
        if cmd == 32770: # alarm reset
            self.response_queue.append(req)
            self.e84_cmd(reset, True)
        elif cmd == 32771: # change mode
            if data == 1:
                self.response_queue.append(req)
                self.e84_cmd(auto, True)
            elif data == 2:
                self.response_queue.append(req)
                self.e84_cmd(manual, True)
        # elif cmd == 'manual':
        #     self.e84_cmd(manual)

    def set_mode(self, port_no, auto_mode=0):

        if auto_mode:  # auto_mode = 1 Auto
            self.mode_bit |= (1 << (port_no-1))
            data_tuple = (self.mode_bit >> 8, self.mode_bit & 0xFF)
            cmd = auto[:-2] + data_tuple
            
        else: # auto_mode = 0 Manual
            self.mode_bit  &= ~(1 << (port_no-1))
            data_tuple = (self.mode_bit >> 8, self.mode_bit & 0xFF)
            cmd = manual[:-2] + data_tuple
        return cmd

    def run_cmd(self, cmd):
        try:
            if self.e84 == None:
                return
            
            if cmd == 'reset':
                print('run_cmd : reset')
                self.e84_cmd(reset, True)
            elif cmd == 'reset2':
                print('run_cmd : reset2')
                self.e84_cmd(reset2, True)
            elif cmd == 'auto':
                print('run_cmd : auto')
                self.e84_cmd(auto, True)
            elif cmd == 'auto2':
                print('run_cmd : auto2')
                self.e84_cmd(auto2, True)
            elif cmd == 'manual':
                print('run_cmd : manual')
                self.e84_cmd(manual, True)
            elif cmd == 'manual2':
                print('run_cmd : manual2')
                self.e84_cmd(manual2, True)
            elif cmd == 'ps_on':
                self.e84_cmd(ps_on, True)
            elif cmd == 'ps_off':
                self.e84_cmd(ps_off, True)
            elif cmd == 'relay_on':
                self.e84_cmd(relay_on, True)
            elif cmd == 'relay_off':
                self.e84_cmd(relay_off, True)
            elif cmd == 'clamp_on':
                self.e84_cmd(clamp_on, True)
            elif cmd == 'clamp_off':
                self.e84_cmd(clamp_off, True)
            elif cmd == 'light_on':
                self.e84_cmd(light_on, True)
            elif cmd == 'light_off':
                self.e84_cmd(light_off, True)
            elif cmd == 'eqer_on':
                self.e84_cmd(eqer_on, True)
            elif cmd == 'eqer_off':
                self.e84_cmd(eqer_off, True)
            elif cmd == 'last_error':
                self.e84_cmd(last_error, True)
            elif cmd == 'check_light_on':
                self.e84_cmd(check_light_on, True)
            elif cmd == 'check_light_off':
                self.e84_cmd(check_light_off, True)
            elif cmd == 'es_on':
                self.e84_cmd(es_on, True)
            elif cmd == 'es_off':
                self.e84_cmd(es_off, True)
            elif cmd == 'version':
                self.e84_cmd(version, True)
            elif cmd == 'mode':
                self.e84_cmd(mode_state, True)
            elif cmd == 'status':
                self.send_status()
            elif cmd == 'status_ledboard':
                self.send_status_ledboard()
            elif cmd == 'alarm_reset':
                print('run_cmd : alarm_reset')
                self._run_coro(self.alarm_reset_async())
            elif cmd.find('alarm') >= 0:
                alarm_id = int(cmd.split()[1])
                self.send_alarm(alarm_id)
            # elif cmd == 'trigger_plc':
            elif cmd.find('trigger_plc') >= 0:
                json_data = {}
                # json_data['port_no'] = 1
                # json_data['Command'] = 'Load'
                json_data['port_no'] = self.port_no[0]
                json_data['Command'] = cmd.split(';')[1]
                self.controller.api_svc.on_notify(json_data)
            elif cmd == 'channel':
                print('run_cmd : channel')
                # asyncio.run(self.open_RF_channel())
                # await self.open_RF_channel()
                self._run_coro(self.open_RF_channel())
            # elif cmd == 'close_RF_channel':
            #     print('run_cmd : close_RF_channel')
            elif cmd == 'continue':
                print('run_cmd : continue')
            elif cmd.find('cs') >= 0:
                print('run_cmd : cs')
                cs = int(cmd.split()[1])
                self._run_coro(self.cs_async(cs))
            elif cmd.find('task') >= 0:
                print('run_cmd : task')
                task = int(cmd.split()[1])
                self._run_coro(self.task_async(task))
            elif cmd.find('handoff') >= 0:
                print('run_cmd : handoff')
                tmp = cmd.split()
                cs = int(tmp[1])
                task = int(tmp[2])
                self._run_coro(self.handoff_async(cs, task))
            elif cmd == 'arm_back':
                print('run_cmd : arm_back')
                self._run_coro(self.arm_back_async())
            

        except Exception as err:
            self.logger.error(str(err))

    def _run_coro(self, coro):
        """Run coro safely: schedule as task when a loop is running, otherwise run to completion."""
        try:
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before get_running_loop")
            loop = asyncio.get_running_loop()
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After get_running_loop succeeded")
        except RuntimeError:
            loop = None
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ loop is None")
        
        if loop and loop.is_running():
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before create_task")
            try:
                loop.create_task(coro)
                print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After create_task succeeded")
            except Exception as err:
                # fallback: try thread-safe submission, or as last resort run in new loop
                print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ create_task failed, falling back:", err)
                try:
                    asyncio.run_coroutine_threadsafe(coro, loop)
                except Exception:
                    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ create_task failed again, falling back to new loop")
                    asyncio.run(coro)
        else:
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before use asyncio.run")
            asyncio.run(coro)
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After use asyncio.run succeeded")

    async def _task_runner(self, coro_func, name, *args, **kwargs):
        """Run coro_func in a loop and restart it if it raises (logs traceback)."""
        while True:
            try:
                print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT Before await coro_func")
                await coro_func(*args, **kwargs)
                print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT After await coro_func")
            except asyncio.CancelledError:
                # Allow cancellation to propagate
                print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT await coro_func CancelledError")
                raise
            except Exception as err:
                self.logger.error(f"TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT {name} crashed: {err}\n{traceback.format_exc()}")
                # wait a bit before restarting
                await asyncio.sleep(1)
                continue
            break

    async def open_RF_channel(self):
        if self.e84 == None:
            return
        if self.e84._state.value != "connected":
            if not await self.e84.connect_async():
                print("❌ 連線失敗，可能原因：")
                print("   1. 串口不存在或已被占用")
                print("   2. 串口權限不足")
                print("   3. 波特率不正確")
                return

        try:
            success = await self.e84.initialize_COMport_RFsensor()
            print(f"######################## initialize E84 RF Sensor 結果: {'成功' if success else '失敗'} ########################")
        finally:
            if self.e84._state.value == "connected":
                await self.e84.disconnect_async()

    async def cs_async(self, cs: int = 0):
        if self.e84 == None:
            return
        success = await self.e84.cobot_cs_async(cs)
        print(f"######################## cs_async 結果: {'成功' if success else '失敗'} ########################")

    async def task_async(self, task: int = 0):
        if self.e84 == None:
            return
        if task == 0:
            success = await self.e84.cobot_load_async()
            print(f"######################## load_async 結果: {'成功' if success else '失敗'} ########################")
        else:
            success = await self.e84.cobot_unload_async()
            print(f"######################## unload_async 結果: {'成功' if success else '失敗'} ########################")

    async def handoff_async(self, cs: int = 0, task: int = 0):
        if self.e84 == None:
            return

        if self.e84._state.value != "connected":
            if not await self.e84.connect_async():
                print("❌ 連線失敗，可能原因：")
                print("   1. 串口不存在或已被占用")
                print("   2. 串口權限不足")
                print("   3. 波特率不正確")
                return
        
        success = await self.e84.cobot_cs_async(cs)
        print(f"######################## cs_async 結果: {'成功' if success else '失敗'} ########################")

        if task == 0:
            success = await self.e84.cobot_load_async()
            print(f"######################## load_async 結果: {'成功' if success else '失敗'} ########################")
        else:
            success = await self.e84.cobot_unload_async()
            print(f"######################## unload_async 結果: {'成功' if success else '失敗'} ########################")

    async def arm_back_async(self):
        if self.e84 == None:
            return
        success = await self.e84.cobot_arm_back_complete_async()
        print(f"######################## arm_back_complete_async 結果: {'成功' if success else '失敗'} ########################")

    async def alarm_reset_async(self):
        if self.e84 == None:
            return
        success = await self.e84.alarm_reset()
        print(f"######################## alarm_reset_async 結果: {'成功' if success else '失敗'} ########################")

    def event_msg(self, data, cs=0):
        try:
            event_msg = list(event71[int(data[1:],16)])
            if data[0] != '0':
                event_msg[2] = str(cs)
            return f"{''.join(event_msg)}"
        except Exception as err:
            self.logger.error(str(err))
            return f"0x{data}"

    def alarm_msg(self, data, cs=0):
        try:
            # alarm_msg = list(alarm80[int(data[1:],16)])
            # alarm_msg[9]=str(cs)
            # return f"0x{data} {''.join(alarm_msg)}"
            return alarm_code[int(data,16)][0]
        except Exception as err:
            self.logger.error(str(err))
            return f"0x{data}"

    def read_rfid(self, cs=0):
        if self.rfid:
            try:
                if settings.MULTIPLE_TYPE:
                    if 'UHF' in self.rfid.type:
                        self.logger.info(f"{self.port_id[0]} read_rfid multi UHF cmd_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                        self.rfid.cmd_read(self.port_no[0])
                        self.rfid_data[0] = self.rfid.rfids[self.port_no[0]-1]
                        self.prev_rfid_data[0] = self.rfid.prev_rfids[self.port_no[0]-1]
                    elif self.rfid.type == 'LF':
                        if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY:
                            self.rfid_data[0] = self.rfid.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[0] = self.rfid.prev_rfids[self.port_no[0]-1]
                        else:
                            # print(type(self.rfid))
                            self.logger.info(f"{self.port_id[0]} read_rfid multi LF sync_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                            self.rfid.sync_read(self.port_no[0], cs, self.rfid_length[cs], self.rfid_order[cs], self.rfid_pattern[cs])
                            self.rfid_data[0] = self.rfid.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[0] = self.rfid.prev_rfids[self.port_no[0]-1]
                    self.logger.info(f"{self.port_id[0]} read carrier_id=[{self.rfid_data[0]}]")
                else: # not settings.MULTIPLE_TYPE

                    if self.mode[cs] != 1: # Manual mode
                            return

                    if settings.DUAL_RFID:
                        rfid_LF = ''
                        prev_rfid_LF = ''
                        rfid_UHF = ''
                        prev_rfid_UHF = ''

                        if self.rfid:
                            self.logger.info(f"{self.port_id[0]} read_rfid dual LF sync_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                            self.rfid.sync_read(self.port_no[0], 0, self.rfid_length[cs], self.rfid_order[cs], self.rfid_pattern[cs])
                            rfid_LF = self.rfid.rfids[self.port_no[0]-1]
                            prev_rfid_LF = self.rfid.prev_rfids[self.port_no[0]-1]
                            if rfid_LF:
                                self.rfid_dual = 0
                                self.rfid_data[self.rfid_dual] = rfid_LF
                                self.prev_rfid_data[self.rfid_dual] = prev_rfid_LF
                        if not rfid_LF:
                            if self.rfid2:
                                self.logger.info(f"{self.port_id[0]} read_rfid dual UHF cmd_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                                self.rfid2.cmd_read(self.port_no[0])
                                rfid_UHF = self.rfid2.rfids[self.port_no[0]-1]
                                prev_rfid_UHF = self.rfid2.prev_rfids[self.port_no[0]-1]
                                if rfid_UHF:
                                    self.rfid_dual = 1
                                    self.rfid_data[self.rfid_dual] = rfid_UHF
                                    self.prev_rfid_data[self.rfid_dual] = prev_rfid_UHF
                    else: # not settings.DUAL_RFID

                        if 'UHF' in self.rfid.type:
                            self.logger.info(f"{self.port_id[cs]} read_rfid UHF cmd_read : cs={cs}, port_no={self.port_no[cs]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                            self.rfid.cmd_read(self.port_no[cs])
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                        elif self.rfid.type == 'LF':
                            if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY:
                                self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                                self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                            else:
                                # print(type(self.rfid))
                                self.logger.info(f"{self.port_id[cs]} read_rfid LF sync_read : cs={cs}, port_no={self.port_no[cs]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                                self.rfid.sync_read(self.port_no[cs], 0, self.rfid_length[cs], self.rfid_order[cs], self.rfid_pattern[cs])
                                self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                                self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                    self.logger.info(f"{self.port_id[cs]} read carrier_id=[{self.rfid_data[cs]}]")
            except Exception as err:
                self.logger.error(f"read_rfid error={str(err)}")

    def clear_rfid(self, cs=0):
        if self.rfid:
            try:
                if self.mode[cs] != 1: # Manual mode
                    return

                if settings.DUAL_RFID:
                    if self.rfid_dual == 0:
                        if self.rfid:
                            self.rfid.clear_rfid(self.port_no[0])
                            self.rfid_data[self.rfid_dual] = self.rfid.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[self.rfid_dual] = self.rfid.prev_rfids[self.port_no[0]-1]
                    elif self.rfid_dual == 1:
                        if self.rfid2:
                            self.rfid2.clear_rfid(self.port_no[0])
                            self.rfid_data[self.rfid_dual] = self.rfid2.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[self.rfid_dual] = self.rfid2.prev_rfids[self.port_no[0]-1]
                else: # not settings.DUAL_RFID
                    if 'UHF' in self.rfid.type:
                        self.rfid.clear_rfid(self.port_no[cs])
                        self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                        self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                    elif self.rfid.type == 'LF':
                        if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY:
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                        else:
                            self.rfid.clear_rfid(self.port_no[cs])
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                self.logger.info(f"{self.port_id[cs]} clear carrier_id=[{self.prev_rfid_data[cs]}]")
            except Exception as err:
                self.logger.error(f"clear_rfid error={str(err)}")

    def manual_read_rfid(self, cs=0):
        if self.rfid:
            try:
                # if self.mode[cs] == 1: # Auto mode
                #     return

                if settings.DUAL_RFID:
                    rfid_LF = ''
                    prev_rfid_LF = ''
                    rfid_UHF = ''
                    prev_rfid_UHF = ''

                    if self.rfid:
                        self.logger.info(f"{self.port_id[0]} manual_read_rfid dual LF sync_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                        self.rfid.sync_read(self.port_no[0], 0, self.rfid_length[cs], self.rfid_order[cs], self.rfid_pattern[cs])
                        rfid_LF = self.rfid.rfids[self.port_no[0]-1]
                        prev_rfid_LF = self.rfid.prev_rfids[self.port_no[0  ]-1]
                        if rfid_LF:
                            self.rfid_dual = 0
                            self.rfid_data[self.rfid_dual] = rfid_LF
                            self.prev_rfid_data[self.rfid_dual] = prev_rfid_LF
                    if not rfid_LF:
                        if self.rfid2:
                            self.logger.info(f"{self.port_id[0]} manual_read_rfid dual UHF cmd_read : cs={cs}, port_no={self.port_no[0]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                            self.rfid2.cmd_read(self.port_no[0])
                            rfid_UHF = self.rfid2.rfids[self.port_no[0]-1]
                            prev_rfid_UHF = self.rfid2.prev_rfids[self.port_no[0]-1]
                            if rfid_UHF:
                                self.rfid_dual = 1
                                self.rfid_data[self.rfid_dual] = rfid_UHF
                                self.prev_rfid_data[self.rfid_dual] = prev_rfid_UHF
                else: # not settings.DUAL_RFID
                    if 'UHF' in self.rfid.type:
                        self.logger.info(f"{self.port_id[cs]} manual_read_rfid UHF cmd_read : cs={cs}, port_no={self.port_no[cs]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                        self.rfid.cmd_read(self.port_no[cs])
                        self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                        self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                    elif self.rfid.type == 'LF':
                        if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY:
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                        else:
                            # print(type(self.rfid))
                            self.logger.info(f"{self.port_id[cs]} manual_read_rfid LF sync_read : cs={cs}, port_no={self.port_no[cs]}, rfid_length={self.rfid_length[cs]}, rfid_order={self.rfid_order[cs]}")
                            self.rfid.sync_read(self.port_no[cs], 0, self.rfid_length[cs], self.rfid_order[cs], self.rfid_pattern[cs])
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                self.logger.info(f"{self.port_id[cs]} manual read carrier_id=[{self.rfid_data[cs]}]")
                # self.logger.info(f"{self.port_id[cs]} port_no={self.port_no[cs]} : place carrier_id [{self.rfid_data[cs]}]")
                msg = f"place carrier_id [{self.rfid_data[cs]}]"
                # self.logger.info(f"{self.port_id[0]} {msg}")
                self.send_event(True, 1, 1, msg, cs)
            except Exception as err:
                self.logger.error(f"manual_read_rfid error={str(err)}")

    def manual_clear_rfid(self, cs=0):
        if self.rfid:
            try:
                # if self.mode[cs] == 1: # Auto mode
                #     return
                
                if settings.DUAL_RFID:
                    if self.rfid_dual == 0:
                        if self.rfid:
                            self.rfid.clear_rfid(self.port_no[0])
                            self.rfid_data[self.rfid_dual] = self.rfid.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[self.rfid_dual] = self.rfid.prev_rfids[self.port_no[0]-1]
                    elif self.rfid_dual == 1:
                        if self.rfid2:
                            self.rfid2.clear_rfid(self.port_no[0])
                            self.rfid_data[self.rfid_dual] = self.rfid2.rfids[self.port_no[0]-1]
                            self.prev_rfid_data[self.rfid_dual] = self.rfid2.prev_rfids[self.port_no[0]-1]
                else: # not settings.DUAL_RFID
                    if 'UHF' in self.rfid.type:
                        self.rfid.clear_rfid(self.port_no[cs])
                        self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                        self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                    elif self.rfid.type == 'LF':
                        if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY:
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                        else:
                            self.rfid.clear_rfid(self.port_no[cs])
                            self.rfid_data[cs] = self.rfid.rfids[self.port_no[cs]-1]
                            self.prev_rfid_data[cs] = self.rfid.prev_rfids[self.port_no[cs]-1]
                self.logger.info(f"{self.port_id[cs]} manual clear carrier_id=[{self.prev_rfid_data[cs]}]")
                # self.logger.info(f"{self.port_id[cs]} port_no={self.port_no[cs]} : remove carrier_id [{self.rfid_data[cs]}]")
                msg = f"remove carrier_id [{self.prev_rfid_data[cs]}]"
                # self.logger.info(f"{self.port_id[0]} {msg}")
                self.send_event(True, 1, 0, msg, cs)
            except Exception as err:
                self.logger.error(f"clear_rfid error={str(err)}")

    def run(self):
        try:
            # self.e84 = serial.Serial(self.devPath, 115200, 8, 'N', 1, timeout=0.25)
            # self.e84.flushInput()
            # self.e84.reset_input_buffer()
            # self.e84_cmd(reset)
            # self.e84_cmd(auto)
            if self.enable:
                self.connect_serial_port()
            
            if self.e84 != None:
                self.e84_cmd(version)
                self.e84_cmd(reset)
                # self.e84_cmd(mode_state)

            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x03)) # simulation mode clamp on
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x01)) # simulation mode clamp off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x00)) # simulation mode ps off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x01)) # simulation mode ps on

            # comment out original E84 schedule jobs
            # schedule.every(10).seconds.do(self.check_connection)
            # schedule.every(1).seconds.do(self.update_state)

        except:
            traceback.print_exc()
            #logger.error('e84 initial connect fail')

        while not self.stop:
            sleep(10)
            continue
            try:
                if self.restart:
                    if self.enable and self.e84:
                        # 0 IDLE
                        # 1 Ready to Load
                        # 2 Ready to Unload
                        # 0x0C = 12 CLAMP ON
                        # 0x22 = 34 CS0 IDLE
                        # 0x14 = 20 Ready to Load (Right)
                        # 0x15 = 21 Ready to Unload (Right)
                        # 0x18 = 24 Load Complete (Right)
                        # 0x19 = 25 Unload Complete (Right)
                        # 0x23 = 35 CS1 IDLE (Right)
                        # 0x26 = 38 CLAMP ON (Right)
                        if (self.port_status[0] < 3 or \
                            # self.port_status == 5 or \
                            # self.port_status == 6 or \
                            # self.port_status == 12 or \
                            self.port_status[0] == 34 ) and \
                            (self.port_status[1] == 20 or \
                            self.port_status[1] == 21 or \
                            # self.port_status2 == 24 or \
                            # self.port_status2 == 25 or \
                            self.port_status[1] == 35):
                            # self.port_status2 == 35 or \
                            # self.port_status2 == 38):
                         
                            self.logger.info(f"{self.port_id[0]} inside restart action")
                            self.disconnect_serial_port()
                            time.sleep(0.5)
                            self.connect_serial_port()
                            if self.e84 != None:
                                self.e84_cmd(link_reset)
                                self.e84_cmd(enable0070)
                                self.e84_cmd(sensor_HRDD_FRSC)
                                # self.e84_cmd(reset)
                                # self.e84_cmd(auto)
                                # if self.dual:
                                #     self.e84_cmd(auto2)
                                self.lastTime = time.time()
                                self.logger.info(f"{self.port_id[0]} restart COM port")
                                self.restart = False
                
                # if self.daily_reconnect:
                #     if self.enable and self.e84:
                #         # 0 IDLE
                #         # 1 Ready to Load
                #         # 2 Ready to Unload
                #         # 0x22 = 34 CS0 IDLE
                #         # 0x14 = 20 Ready to Load (Right)
                #         # 0x15 = 21 Ready to Unload (Right)
                #         # 0x23 = 35 CS1 IDLE (Right)
                #         if (self.port_status[0] < 2 ) and \
                #             (self.port_status[1] == 35):
                         
                #             self.logger.info(f"{self.port_id[0]} inside daily reconnect COM port")
                #             self.disconnect_serial_port()
                #             time.sleep(0.1)
                #             self.connect_serial_port()
                #             if self.e84 != None:
                #                 # self.e84_cmd(link_reset)
                #                 self.e84_cmd(enable0070)
                #                 # self.e84_cmd(reset)
                #                 # self.e84_cmd(auto)
                #                 # if self.dual:
                #                 #     self.e84_cmd(auto2)
                #                 self.lastTime = time.time()
                #                 self.logger.info(f"{self.port_id[0]} daily reconnect COM port")
                #                 self.daily_reconnect = False
                #                 self.daily_reconnect_time = datetime.now()
                    
                if (not self.enable) and self.e84:
                    self.disconnect_serial_port()
                    if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                        for m in range(0, self.dual+1):
                            self.rfid.access_mode[self.port_no[m]-1] = 0
                    for m in range(0, self.dual+1):
                        self.mode[m] = 0 # Why you need to set 0 ?
                        self.send_event2(server=True, stream=6, function=11, code=0, subcode=2, msg_text="disable COM port", cs=m)
                        # if self.port_no2 > 0:
                        #     self.mode2 = 0 # Why you need to set 0 ?
                        #     self.send_event2(server=True, stream=6, function=11, code=0, subcode=2, msg_text="disable COM port", dual=self.port_no2)
        
                if not self.enable:
                    time.sleep(5)
                    continue

                if self.e84 == None:
                    self.connect_serial_port()
                    if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                        for m in range(0, self.dual+1):
                            self.rfid.access_mode[self.port_no[m]-1] = 2
                    for m in range(0, self.dual+1):
                        self.mode[m] = 2 # Why you need to set 2 ?
                        self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port", cs=m)
                    # self.mode = 2 # Why you need to set 2 ?
                    # self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port")
                    # if self.port_no2 > 0:
                    #     self.mode2 = 2 # Why you need to set 2 ?
                    #     self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port", dual=self.port_no2)
                    if self.e84 != None:
                        self.e84_cmd(reset)
                        # self.e84_cmd(auto)
                    self.lastTime = time.time()
                    time.sleep(1)
                    continue

                # Get the current time
                # current_time = datetime.now().time()
                current_time = datetime.now()

                # Check if the current time is 10:00 AM
                # if current_time.hour == 10 and current_time.minute == 0 and current_time.second <= 6 and not self.daily_reconnect:
                # if current_time.hour == 10 and not self.daily_reconnect:
                #     time_diff = current_time - self.daily_reconnect_time

                #     # Check if the time difference is greater than 60 seconds
                #     # if time_diff > timedelta(seconds=60):
                #     # if time_diff.total_seconds() >= 180:
                #     if time_diff.days >= 1:
                #         self.daily_reconnect = True

                # # if len(self.e84_queue) < 1:
                # #     schedule.run_pending()

                # # e84 write
                # if len(self.e84_queue) > 0:
                #     if self.e84 == None:
                #         continue
                #     else:
                #         self.e84.write(self.e84_queue.popleft())

                # res = self.e84.read(8) # <class 'bytes'>
                # res = self.e84.read(timeout=0.5)
                res = self.read(timeout=0.5)

                if res is None or res == '':
                    # self.logger.info(f"############ run read is Null")
                    continue

                # print('tmp', res)
                if settings.E84_THREAD_DEBUG_ENABLE:
                    self.logger.info(f"{self.port_id[0]} ############ run read {res.hex()}")
                if len(res) != 8:
                    if len(res) > 0:
                        self.logger.info(f"{self.port_id[0]} Warning : read length != 8, res : {res}")
                    # schedule.run_pending()
                    continue
                #print(self.port_id, ' res: ', res)

                # check data
                if type(res) == str: # python2
                    res_b = struct.unpack('<BBBBBBBB', res)
                    if sum(res_b[0:7])%256 != res_b[7]:
                        self.logger.info(f"{self.port_id[0]} E84 check sum error")
                        # self.restart = True
                        continue
                    res = res.encode('hex')
                elif type(res) == bytes: # python3
                    if sum(res[0:7])%256 != res[7]:
                        self.logger.info(f"{self.port_id[0]} E84 check sum error")
                        # self.restart = True
                        continue
                    res = res.hex()
                
                self.count = 0
                self.lastTime = time.time()
                
                if self.errorCode == 7777:
                    # self.state['alarm'] = False
                    self.errorCode = 0
                    self.errorMsg = ''
                    self.port_connected = 0
                    #logger.error('e84 reconnected')
                    # self.port_status = 6
                    # self.alarm_id = 0
                    # self.alarm_text = ''
                    # self.send_event(True, int('0090',16), 1, 'E84 reconnected')
                    # if self.port_no2 > 0:
                    #     self.send_event(server=True, code=int('0090',16), subcode=1, msg_text="E84 reconnected", dual=self.port_no2)
                    for m in range(self.dual+1):
                        self.send_event(server=True, code=int('0090',16), subcode=1, msg_text="E84 reconnected", cs=m)
                    self.logger.info(f"{self.port_id[0]} E84 reconnected")
                    self.e84_cmd(reset)
                    # self.e84_cmd(auto)
                    if self.dual:
                        self.e84_cmd(reset2)
                        # self.e84_cmd(auto2)
                    self.e84_cmd(mode_state)

                cmd = res[4:8]
                data = res[8:12]
                status = res[12:14]
                # print(cmd, data, status)

                if status == '00':
                    pass # success
                elif status == '01':
                    self.logger.info(f"{self.port_id[0]} E84 : This alarm will be auto recover {cmd}:{data} {status}")
                elif status == '02':
                    self.logger.info(f"{self.port_id[0]} E84 : Command is denied in current condition {cmd}:{data} {status}")
                    continue
                elif status == '03':
                    self.logger.info(f"{self.port_id[0]} E84 : Do not support this command {cmd}:{data} {status}")
                    continue
                elif status == '04':
                    self.logger.info(f"{self.port_id[0]} E84 : Command data is invalid {cmd}:{data} {status}")
                    continue
                elif status == '05' or status == '15':
                    self.logger.info(f"{self.port_id[0]} E84 : This alarm have to be manual reset by operator {cmd}:{data} {status}")

                msg = ''
                if cmd == '0000':
                    # data1 = int(data[0:2], 16)
                    # data2 = int(data[2:4], 16)
                    # self.led['power'] = True
                    #print('e84 connecting')
                    # self.power = 1 if self.led['power'] else 0
                    ## 0 : E84, 1 : E87, 2 : LF-RFID, 3 : UHF-RFID
                    # self.send_event(True, int(cmd, 16), int(data, 16), f'Firmware version {data[0:2]}.{data[2:4]}')
                    # if self.port_no2 > 0:
                    #     self.send_event(server=True, code=int(cmd, 16), subcode=int(data, 16), msg_text=f'Firmware version {data[0:2]}.{data[2:4]}', dual=self.port_no2)
                    self.e84_dual = 2 if data[0:1] == '2' else 1
                    self.fw_version = f"{data[0:2]}.{data[2:4]}"
                    for m in range(self.dual+1):
                        self.send_event(server=True, code=int(cmd, 16), subcode=int(data, 16), msg_text=f'Firmware version {data[0:2]}.{data[2:4]}', cs=m)
                    msg = cmd + ':' + data + ':' + status + ' Firmware version'

                elif cmd == '000f':
                    self.led['power'] = True
                    #print('e84 connecting')
                    self.power = 1 if self.led['power'] else 0
                    ## 0 : E84, 1 : E87, 2 : LF-RFID, 3 : UHF-RFID
                    # self.mqtt_publish(int(cmd, 16), int(data, 16), 'E84 connected')
                    msg = cmd + ':' + data + ':' + status + ' Product code'
                    # self.logger.info(f"{self.port_id} {msg}")
                    continue
                    
                elif cmd == '8002' or cmd == '0002':
                    # if data == '0000' and status == '00':
                        #print(cmd, data,status)
                    # self.state['alarm'] = False
                    # self.state['loading'] = False
                    # self.state['unloading'] = False
                    # self.state['load_complete'] = False
                    # self.state['unload_complete'] = False
                    # self.port_status = 6
                    # self.alarm_id = 0
                    # self.alarm_text = ''
                    m = 0 if data == '0000' else 1
                    self.send_event(True, int(cmd, 16), int(data, 16), 'Alarm Reset', m)
                    # self.e84_cmd(auto)
                    # self.mqtt_publish(int(cmd, 16), int(data, 16), 'alarm reset')
                    msg = cmd + ':' + data + ':' + status + ' Alarm Reset'
                    # self.e84_cmd(last_error)

                    if settings.CLAMP_ENABLE:
                        self.e84_cmd(clamp_off, True)

                    if settings.DOOR:
                        self.e84_cmd(relay_off, True)

                    if settings.LED_ENABLE:
                        self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                elif cmd == '8003':
                    if data == '0000':
                        # self.state['manual'] = True
                        # self.state['auto'] = False
                        # self.state['start_to_load'] = False
                        # self.state['start_to_unload'] = False
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[0]-1] = 2
                        self.mode[0] = 2
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Change to Manual')
                        msg = cmd + ':' + data + ':' + status + ' Change to Manual'
                        
                    elif data == '0001':
                        # self.state['auto'] = True
                        # self.state['manual'] = False
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[0]-1] = 1
                        self.mode[0] = 1
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Change to Auto')
                        msg = cmd + ':' + data + ':' + status + ' Change to Auto'
                    elif data == '0100':
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[1]-1] = 2
                        self.mode[1] = 2
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Change to Manual2', 1)
                        msg = cmd + ':' + data + ':' + status + ' Change to Manual2'
                    elif data == '0101':
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[1]-1] = 1
                        self.mode[1] = 1
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Change to Auto2', 1)
                        msg = cmd + ':' + data + ':' + status + ' Change to Auto2'
                elif cmd == '0003': # seems like useless
                    if data == '0000':
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[0]-1] = 2
                        self.mode[0] = 2
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Manual')
                        msg = cmd + ':' + data + ':' + status + ' State: Manual'
                    elif data == '0001':
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[0]-1] = 1
                        self.mode[0] = 1
                        self.send_event(True, int(cmd, 16), int(data, 16), 'Auto')
                        msg = cmd + ':' + data + ':' + status + ' State: Auto'
                elif cmd == '8019':
                    data2 = int(data[2:4], 16)
                    if data2 != 0:
                        # self.state['ps'] = True
                        if self.pspl != data2 :
                            self.pspl = data2
                            self.send_event(True, int(cmd, 16), data2, 'Set PS/PL ON')
                        msg = cmd + ':' + data[2:4] + ':' + status + '   Set PS/PL ON'
                    elif data2 == 0:
                        # self.state['ps'] = False
                        if self.pspl != data2 :
                            self.pspl = data2
                            self.send_event(True, int(cmd, 16), data2, 'Set PS/PL OFF')
                        msg = cmd + ':' + data[2:4] + ':' + status + '   Set PS/PL OFF'
                elif cmd == '0019':
                    data2 = int(data[2:4], 16)
                    p1 =  data2&0x01
                    p2 =  (data2&0x02)>>1
                    p3 =  (data2&0x04)>>2
                    p4 =  (data2&0x08)>>3
                    p5 =  (data2&0x10)>>4
                    p6 =  (data2&0x20)>>5
                    p7 =  (data2&0x40)>>6
                    p8 =  (data2&0x80)>>7
                    # self.pspl = True if p1 and p2 and p3 and p4 else False
                    if self.pspl != data2 :
                        self.pspl = data2
                        # self.send_event(True, int(cmd, 16), data2, 'pspl')
                        if settings.E84_TYPE == 1:
                            msg = cmd + ':' + data[2:4] + ':' + status + f"   pspl : PL1: {p1} PL2: {p2} PL3: {p3} PL4: {p4} PL5: {p5} PL6: {p6} PL7: {p7} PL8: {p8}"
                        else:
                            msg = cmd + ':' + data[2:4] + ':' + status + f"   pspl : SE1: {p1} SE2: {p2} SE3: {p3} SE4: {p4} SE5: {p5} SE6: {p6} SE7: {p7} SE8: {p8}"
                        self.logger.info(f"{self.port_id[0]} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        if settings.E84_TYPE == 0:
                            if self.mode[0] == 2:
                                if p1 and p2:
                                    self.manual_read_rfid()
                                elif  self.pspl != -1 and p1 == 0 and p2 == 0:
                                    self.manual_clear_rfid()
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                    # print('0019 pspl : ', data[2:4]) #, p1, p2, p3, p4)
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   pspl : SE1: {p1} SE2: {p2} SE3: {p3} SE4: {p4} SE5: {p5} SE6: {p6} SE7: {p7} SE8: {p8}"
                    continue
                elif cmd == '0104':
                    data2 = int(data[2:4], 16)
                    p1 =  data2&0x01
                    p2 =  (data2&0x02)>>1
                    p3 =  (data2&0x04)>>2
                    p4 =  (data2&0x08)>>3
                    p5 =  (data2&0x10)>>4
                    p6 =  (data2&0x20)>>5
                    p7 =  (data2&0x40)>>6
                    p8 =  (data2&0x80)>>7
                    # self.pspl = True if p1 and p2 and p3 and p4 else False
                    if self.pspl2 != data2 :
                        self.pspl2 = data2
                        # self.send_event(True, int(cmd, 16), data2, 'pspl')
                        msg = cmd + ':' + data[2:4] + ':' + status + f"   pspl2 : PS1: {p1} PS2: {p2} PS3: {p3} PS4: {p4} PS5: {p5} PS6: {p6} PS7: {p7} PS8: {p8}"
                        self.logger.info(f"{self.port_id[0]} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                    # print('0019 pspl : ', data[2:4]) #, p1, p2, p3, p4)
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   pspl : SE1: {p1} SE2: {p2} SE3: {p3} SE4: {p4} SE5: {p5} SE6: {p6} SE7: {p7} SE8: {p8}"
                    continue
                elif cmd == '0125':
                    data2 = int(data, 16)
                    msg2 = 'Relay OFF'
                    if data2 > 0:
                        msg2 = 'Relay ON'
                    if self.relay != data2 :
                        self.relay = data2
                        # self.send_event(False, int(cmd, 16), data2, msg2)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        msg = cmd + ':' + data + ':' + status + ' ' + msg2
                        self.logger.info(f"{self.port_id[0]} {msg}")
                    continue
                elif cmd == '8125':
                    data2 = int(data, 16)
                    msg2 = 'Change to Relay OFF'
                    if data2 > 0:
                        msg2 = 'Change to Relay ON'
                    if self.relay != data2 :
                        self.relay = data2
                        self.send_event(False, int(cmd, 16), data2, msg2)
                    msg = cmd + ':' + data + ':' + status + ' ' + msg2
                elif cmd == '0049': # Read Last Error Code
                    msg = cmd + ':' + data + ':' + status + ' Last Alarm Code'
                    # alarm_id = int(data, 16)
                    # alarm_status = int(status, 16)

                    # if self.alarm_id[0] != alarm_id:
                    
                    #     if alarm_id == 0 and alarm_status == 0:
                    #         self.alarm_id[0] = 0
                    #         self.alarm_text[0] = ''
                    #         msg = cmd + ':' + data + ':' + status + ' Alarm Solve'
                    #         self.logger.info(f"{self.port_id[0]} {msg}")
                    #         self.send_event(True, int(cmd, 16), alarm_id, msg)
                    #     else:
                    #         self.alarm_id[0] = alarm_id
                    #         try:
                    #             # self.alarm_text = e84_err_code[alarm_id]
                    #             # self.send_event(True, int(cmd, 16), alarm_id, e84_err_code[alarm_id])
                    #             # self.alarm_text[0] = ftp_alarmlist['S05F01'][128][alarm_id]['msgtext']
                    #             self.alarm_text[0] = alarm_code[self.alarm_id[0]][0]
                    #             msg = cmd + ':' + data + ':' + status + f" Alarm : {self.alarm_id[0]}, {self.alarm_text[0]}"
                    #             self.logger.info(f"{self.port_id[0]} {msg}")
                    #             self.send_event(True, int(cmd, 16), alarm_id, self.alarm_text[0])
                    #         except Exception as err:
                    #             self.alarm_text[0] = 'Alarm code not in database list'
                    #             msg = cmd + ':' + data + ':' + status + f" Alarm : {self.alarm_id[0]}, {self.alarm_text[0]}"
                    #             self.logger.info(f"{self.port_id[0]} {msg}")
                    #             self.send_event(True, int(cmd, 16), alarm_id, self.alarm_text[0])
                    m = int(status[0])
                    self.logger.info(f"{self.port_id[m]} {msg}")
                    continue
                    
                elif cmd == '001c':
                    msg = cmd + ':' + data + ' Mode State'
                    dt = int(data, 16)
                    bPrint = False
                    # self.load = 1 if dt & 0x0003 > 0 else 0
                    mode = 1 if dt & 0x0004 > 0 else 2  # Access Mode 0: Unknown, 1: Auto, 2: Manual
                    # print('#### 001c load : ', 1 if dt & 0x0003 > 0 else 0)
                    # print(self.port_id, 'e84: {}:{}'.format(msg, 1 if dt & 0x0003 > 0 else 0))
                    if self.mode[0] != mode:
                        if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                            if self.rfid:
                                self.rfid.access_mode[self.port_no[0]-1] = mode
                        self.mode[0] = mode
                        if mode == 1:
                            mode_msg = 'Auto'
                        else:
                            mode_msg = 'Manual'
                        msg = cmd + ':' + data + ':' + status + f" Mode : {mode_msg}"
                        self.logger.info(f"{self.port_id[0]} {msg}")
                        self.send_event(True, int(cmd, 16), int(data, 16), mode_msg)
                        bPrint = True

                    port_status = 2 if dt & 0x0001 > 0 else 1  # 1: Ready to Load, 2: Ready to Unload
                    if self.port_status[0] != port_status:
                        self.port_status[0] = port_status
                        if port_status == 1:
                            self.port_status_msg[0] = 'Ready to Load'
                            self.clear_rfid()
                        else:
                            self.port_status_msg[0] = 'Ready to Unload'
                            if settings.MULTIPLE_TYPE:
                                if not self.sensor_HRDD_FRSC['home']:
                                    self.read_rfid(1)
                                else:
                                    self.read_rfid()
                            else:
                                self.read_rfid()
                        msg = cmd + ':' + data + ':' + status + f" State : {self.port_status_msg[0]}"
                        self.logger.info(f"{self.port_id[0]} {msg}")
                        self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg[0])
                        bPrint = True

                    if not bPrint:
                        self.logger.info(f"{self.port_id[0]} {msg}")

                    if self.dual:
                        bPrint = False
                        mode = 1 if dt & 0x0400 > 0 else 2  # Access Mode 0: Unknown, 1: Auto, 2: Manual
                        if self.mode[1] != mode:
                            if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                                if self.rfid:
                                    self.rfid.access_mode[self.port_no[1]-1] = mode
                            self.mode[1] = mode
                            if mode == 1:
                                mode_msg = 'Auto2'
                            else:
                                mode_msg = 'Manual2'
                            msg = cmd + ':' + data + ':' + status + f" Mode2 : {mode_msg}"
                            self.logger.info(f"{self.port_id[1]} {msg}")
                            self.send_event(True, int(cmd, 16), int(data, 16), mode_msg, 1)
                            bPrint = True

                        port_status = 21 if dt & 0x0100 > 0 else 20  # 20: Ready to Load (Right), 21: Ready to Unload (Right)
                        if self.port_status[1] != port_status:
                            self.port_status[1] = port_status
                            if port_status == 1:
                                self.port_status_msg[1] = 'Ready to Load (Right)'
                                self.clear_rfid(1)
                            else:
                                self.port_status_msg[1] = 'Ready to Unload (Right)'
                                self.read_rfid(1)
                            msg = cmd + ':' + data + ':' + status + f" State2 : {self.port_status_msg[1]}"
                            self.logger.info(f"{self.port_id[1]} {msg}")
                            self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg[1], 1)
                            bPrint = True

                        if not bPrint:
                            self.logger.info(f"{self.port_id[1]} {msg}")
                    continue
                elif cmd == '8013':
                    msg = cmd + ':' + data + ':' + status + ' Enable 0070 function'
                elif cmd == '0052' or cmd == '8052':
                    # self.send_event(True, int(cmd, 16), int(data, 16), 'link connection report')
                    msg = cmd + ':' + data + ':' + status + ' Link Connection Report'
                elif cmd == '0057' or cmd == '8057':
                    msg = cmd + ':' + data + ':' + status + ' Unknown'
                elif cmd == '0104':
                    msg = cmd + ':' + data + ':' + status + ' Unknown'
                    continue
                elif cmd == '0118':
                    data2 = int(data[2:4], 16)
                    self.sensor_HRDD_FRSC['carrier'] = 1 if data2&0x01 else 0
                    self.sensor_HRDD_FRSC['standby'] = 1 if data2&0x02 else 0
                    self.sensor_HRDD_FRSC['run'] = 1 if data2&0x04 else 0
                    self.sensor_HRDD_FRSC['finish'] = 1 if data2&0x08 else 0
                    self.sensor_HRDD_FRSC['door_open'] = 1 if data2&0x10 else 0
                    self.sensor_HRDD_FRSC['door_close'] = 1 if data2&0x20 else 0
                    self.sensor_HRDD_FRSC['ready'] = 1 if data2&0x40 else 0
                    
                    if settings.MULTIPLE_TYPE:
                        tmp_home = 1 if data2&0x80 else 0
                        if self.port_status[0] != 5: # not in Load Complete, Tool in Process mode
                            self.sensor_HRDD_FRSC['home'] = 1 if data2&0x80 else 0
                        else: # in Load Complete, Tool in Process mode
                            # self.logger.info(f"{self.port_id[0]} Tool in Process mode, ignore Home sensor signal")
                            pass
                    else:
                        self.sensor_HRDD_FRSC['home'] = 1 if data2&0x80 else 0
                    
                    if self.sensor_hrdd_frsc != data2:
                        # if settings.MULTIPLE_TYPE:
                        #     if self.sensor_HRDD_FRSC['home']:
                        #         self.e84_cmd(inch12_off, True)
                        #     else:
                        #         self.e84_cmd(inch12_on, True)
                        
                        self.sensor_hrdd_frsc = data2
                        if settings.MULTIPLE_TYPE:
                            msg = cmd + ':' + data[2:4] + ':' + status + f"   Reg_Home: {self.sensor_HRDD_FRSC['home']}  Home: {tmp_home}  Ready: {self.sensor_HRDD_FRSC['ready']}  Door_Close: {self.sensor_HRDD_FRSC['door_close']}  Door_Open: {self.sensor_HRDD_FRSC['door_open']}  Finish: {self.sensor_HRDD_FRSC['finish']}  Run: {self.sensor_HRDD_FRSC['run']}  Standby: {self.sensor_HRDD_FRSC['standby']}  Carrier: {self.sensor_HRDD_FRSC['carrier']} "
                        else:
                            msg = cmd + ':' + data[2:4] + ':' + status + f"   Home: {self.sensor_HRDD_FRSC['home']}  Ready: {self.sensor_HRDD_FRSC['ready']}  Door_Close: {self.sensor_HRDD_FRSC['door_close']}  Door_Open: {self.sensor_HRDD_FRSC['door_open']}  Finish: {self.sensor_HRDD_FRSC['finish']}  Run: {self.sensor_HRDD_FRSC['run']}  Standby: {self.sensor_HRDD_FRSC['standby']}  Carrier: {self.sensor_HRDD_FRSC['carrier']} "
                        self.logger.info(f"{self.port_id[0]} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        # self.mqtt_publish(int(cmd, 16), data2, 'EQ_ER, LIGHT, CLAMP, ES')
                    # print('0016:', data[2:4], 'EQ_ER, LIGHT, CLAMP, ES')
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   EQ_ER: {self.gpio2['eq_er']}  LIGHT: {self.gpio2['light']}  CLAMP: {self.gpio2['clamp']}  ES: {self.gpio2['es']} "
                    continue
                elif cmd == '8143':
                    data2 = int(data, 16)
                    if data2:
                        msg = cmd + ':' + data + ':' + status + ' Set FOUP 12'
                    else:
                        msg = cmd + ':' + data + ':' + status + ' Set FOUP 8'
                    self.logger.info(f"{self.port_id[0]} {msg}")
                    continue
                elif cmd == '011b':
                    msg = cmd + ':' + data + ':' + status + ' Unknown'
                    continue
                elif cmd == '0010':
                    data2 = int(data[2:4], 16)
                    self.led['l_req'] = 1 if data2&0x01 else 0
                    self.led['u_req'] = 1 if data2&0x02 else 0
                    self.led['va'] = 1 if data2&0x04 else 0
                    self.led['ready'] = 1 if data2&0x08 else 0
                    self.led['vs_0'] = 1 if data2&0x10 else 0
                    self.led['vs_1'] = 1 if data2&0x20 else 0
                    self.led['ho_avbl'] = 1 if data2&0x40 else 0
                    self.led['es'] = 1 if data2&0x80 else 0
                    if self.e84_out != data2:
                        self.e84_out = data2
                        msg = cmd + ':' + data[2:4] + ':' + status + f"   OUT : ES: {self.led['es']}  HO_AVBL: {self.led['ho_avbl']}  VS_1: {self.led['vs_1']}  VS_0: {self.led['vs_0']}  READY: {self.led['ready']}  VA: {self.led['va']}  U_REQ: {self.led['u_req']}  L_REQ: {self.led['l_req']} "
                        # self.logger.info(f"{self.port_id} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        # self.mqtt_publish(int(cmd, 16), data2, 'E84 output')
                    # print('0010:', data[2:4], 'OUT : ES, HO_AVBL, VS_1, VS_0, READY, VA, U_REQ, L_REQ')
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   OUT : ES: {self.led['es']}  HO_AVBL: {self.led['ho_avbl']}  VS_1: {self.led['vs_1']}  VS_0: {self.led['vs_0']}  READY: {self.led['ready']}  VA: {self.led['va']}  U_REQ: {self.led['u_req']}  L_REQ: {self.led['l_req']} "
                    continue
                elif cmd == '0011':
                    data2 = int(data[2:4], 16)
                    self.led['valid'] = 1 if data2&0x01 else 0
                    self.led['cs_0'] = 1 if data2&0x02 else 0
                    self.led['cs_1'] = 1 if data2&0x04 else 0
                    self.led['am_avbl'] = 1 if data2&0x08 else 0
                    self.led['tr_req'] = 1 if data2&0x10 else 0
                    self.led['busy'] = 1 if data2&0x20 else 0
                    self.led['compt'] = 1 if data2&0x40 else 0
                    self.led['cont'] = 1 if data2&0x80 else 0
                    if self.e84_in != data2:
                        self.e84_in = data2
                        msg = cmd + ':' + data[2:4] + ':' + status + f"   IN : CONT: {self.led['cont']}  COMPT: {self.led['compt']}  BUSY: {self.led['busy']}  TR_REQ: {self.led['tr_req']}  AM_AVBL: {self.led['am_avbl']}  CS_1: {self.led['cs_1']}  CS_0: {self.led['cs_0']}  VALID: {self.led['valid']} "
                        # self.logger.info(f"{self.port_id} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        # self.mqtt_publish(int(cmd, 16), data2, 'E84 input')
                    # print('0011:', data[2:4], 'IN : CONT, COMPT, BUSY, TR_REQ, AM_AVBL, CS_1, CS_0, VALID')
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   IN : CONT: {self.led['cont']}  COMPT: {self.led['compt']}  BUSY: {self.led['busy']}  TR_REQ: {self.led['tr_req']}  AM_AVBL: {self.led['am_avbl']}  CS_1: {self.led['cs_1']}  CS_0: {self.led['cs_0']}  VALID: {self.led['valid']} "
                    continue
                elif cmd == '0012':
                    data2 = int(data[2:4], 16)
                    self.gpio1['go'] = 1 if data2&0x01 else 0
                    self.gpio1['mode'] = 1 if data2&0x02 else 0
                    self.gpio1['select'] = 1 if data2&0x04 else 0
                    if self.e84_smg != data2:
                        self.e84_smg = data2
                        msg = cmd + ':' + data[2:4] + ':' + status + f"   SELECT: {self.gpio1['select']}  MODE: {self.gpio1['mode']}  GO: {self.gpio1['go']} "
                        # self.logger.info(f"{self.port_id} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        # self.mqtt_publish(int(cmd, 16), data2, 'SELECT, MODE, GO')
                    # print('0012:', data[2:4], 'SELECT, MODE, GO')
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   SELECT: {self.gpio1['select']}  MODE: {self.gpio1['mode']}  GO: {self.gpio1['go']} "
                    continue
                elif cmd == '0016' or cmd == '8016':
                    data2 = int(data[2:4], 16)
                    self.gpio2['es'] = 1 if data2&0x01 else 0
                    self.gpio2['clamp'] = 1 if data2&0x02 else 0
                    self.gpio2['light'] = 1 if data2&0x04 else 0
                    self.gpio2['eq_er'] = 1 if data2&0x08 else 0
                    if self.sensor_elce != data2:
                        self.sensor_elce = data2
                        msg = cmd + ':' + data[2:4] + ':' + status + f"   EQ_ER: {self.gpio2['eq_er']}  LIGHT: {self.gpio2['light']}  CLAMP: {self.gpio2['clamp']}  ES: {self.gpio2['es']} "
                        # self.logger.info(f"{self.port_id} {msg}")
                        # self.send_event(False, int(cmd, 16), data2, msg)
                        for m in range(self.dual+1):
                            self.send_event(False, int(cmd, 16), data2, msg, cs=m)
                        # self.mqtt_publish(int(cmd, 16), data2, 'EQ_ER, LIGHT, CLAMP, ES')
                    # print('0016:', data[2:4], 'EQ_ER, LIGHT, CLAMP, ES')
                    # continue
                    # msg = cmd + ':' + data[2:4] + f"   EQ_ER: {self.gpio2['eq_er']}  LIGHT: {self.gpio2['light']}  CLAMP: {self.gpio2['clamp']}  ES: {self.gpio2['es']} "
                    continue
                elif cmd == '001a' or cmd == '801a':
                    data2 = int(data[2:4], 16)
                    if self.pspl_usage != data2:
                        self.pspl_usage = data2
                        # self.mqtt_publish(int(cmd, 16), data2, 'pspl usage')
                    # print(cmd, 'pspl usage : ', data)
                    msg = cmd + ':' + data[2:4] + ':' + status + '   PS/PL Usage'
                elif cmd == '001b' or cmd == '801b':
                    data2 = int(data[2:4], 16)
                    if self.pspl_setting != data2:
                        self.pspl_setting = data2
                        # self.mqtt_publish(int(cmd, 16), data2, 'pspl setting')
                    # print(cmd, 'sensor setting : ', data)
                    msg = cmd + ':' + data[2:4] + ':' + status + '   PS/PL Setting'

                elif cmd == '0070':
                    if data == '0000':
                        # self.state['go'] = True
                        msg = 'GO ON'
                    elif data == '0001':
                        # self.state['go'] = False
                        msg = 'GO OFF'
                    elif data == '0002':
                        # self.state['valid'] = True
                        msg = 'VALID ON'
                        if settings.LED_ENABLE:
                            self.controller.led_controller.turn_on_channel(self.led_id, timeout=1.5)
                    elif data == '0003':
                        # self.state['valid'] = False
                        msg = 'VALID OFF'
                    elif data == '0004':
                        # self.state['cs_0'] = True
                        msg = 'CS_0 ON'
                    elif data == '0005':
                        # self.state['cs_0'] = False
                        msg = 'CS_0 OFF'
                    elif data == '0006':
                        # self.state['cs_1'] = True
                        msg = 'CS_1 ON'
                    elif data == '0007':
                        # self.state['cs_1'] = False
                        msg = 'CS_1 OFF'
                    elif data == '0008':
                        # self.state['am_avbl'] = True
                        msg = 'AM_AVBL ON'
                    elif data == '0009':
                        # self.state['am_avbl'] = False
                        msg = 'AM_AVBL OFF'
                    elif data == '000a':
                        # self.state['tr_req'] = True
                        msg = 'TR_REQ ON'
                        if settings.DOOR:
                            self.e84_cmd(relay_on, True)
                    elif data == '000b':
                        # self.state['tr_req'] = False
                        msg = 'TR_REQ OFF'
                    elif data == '000c':
                        # self.state['busy'] = True
                        msg = 'BUSY ON'
                    elif data == '000d':
                        # self.state['busy'] = False
                        msg = 'BUSY OFF'
                    elif data == '000e':
                        # self.state['compt'] = True
                        msg = 'COMPT ON'
                    elif data == '000f':
                        # self.state['compt'] = False
                        msg = 'COMPT OFF'
                    elif data == '0010':
                        # self.state['cont'] = True
                        msg = 'CONT ON'
                    elif data == '0011':
                        # self.state['cont'] = False
                        msg = 'CONT OFF'
                    elif data == '0012':
                        # self.state['l_req'] = True
                        msg = 'L_REQ ON'
                    elif data == '0013':
                        # self.state['l_req'] = False
                        msg = 'L_REQ OFF'
                        # if self.rfid:
                        #     if self.rfid.type == 'LF':
                        #         if self.cs >= 0:
                        #             # 1, 3, 5
                        #             rfid_idx = self.cs*2+1
                        #             self.rfid.sync_read(rfid_idx+1)
                        #             self.rfid_data[self.cs] = self.rfid.rfids[rfid_idx]
                        #             self.logger.info(f"{self.port_id[self.cs]} {cmd}:{data} CassetteID={self.rfid_data[self.cs]}")
                    elif data == '0014':
                        # self.state['u_req'] = True
                        msg = 'U_REQ ON'
                    elif data == '0015':
                        # self.state['u_req'] = False
                        msg = 'U_REQ OFF'
                        # if self.rfid:
                        #     if self.rfid.type == 'LF':
                        #         if self.cs >= 0:
                        #             # 1, 3, 5
                        #             rfid_idx = self.cs*2+1
                        #             self.rfid.rfids[rfid_idx] = ''
                        #             self.rfid_data[self.cs] = self.rfid.rfids[rfid_idx]
                        #             self.logger.info(f"{self.port_id[self.cs]} {cmd}:{data} CassetteID={self.rfid_data[self.cs]}")
                    elif data == '0016':
                        # self.state['va'] = True
                        msg = 'VA ON'
                    elif data == '0017':
                        # self.state['va'] = False
                        msg = 'VA OFF'
                    elif data == '0018':
                        # self.state['ready'] = True
                        msg = 'READY ON'
                    elif data == '0019':
                        # self.state['ready'] = False
                        msg = 'READY OFF'
                    elif data == '001a':
                        # self.state['vs_0'] = True
                        msg = 'VS_0 ON'
                    elif data == '001b':
                        # self.state['vs_0'] = False
                        msg = 'VS_0 OFF'
                    elif data == '001c':
                        # self.state['vs_1'] = True
                        msg = 'VS_1 ON'
                    elif data == '001d':
                        # self.state['vs_1'] = False
                        msg = 'VS_1 OFF'
                    elif data == '001e':
                        # self.state['hoavbl'] = True
                        msg = 'HOAVBL ON'
                        self.send_status()
                    elif data == '001f':
                        # self.state['hoavbl'] = False
                        msg = 'HOAVBL OFF'
                    elif data == '0020':
                        # self.state['es'] = True
                        msg = 'ES ON'
                    elif data == '0021':
                        # self.state['es'] = False
                        msg = 'ES OFF'
                    elif data == '0022':
                        # self.state['mode'] = True
                        msg = 'MODE ON'
                    elif data == '0023':
                        # self.state['mode'] = False
                        msg = 'MODE OFF'
                    elif data == '0024':
                        # self.state['select'] = True
                        msg = 'SELECT ON'
                    elif data == '0025':
                        # self.state['select'] = False
                        msg = 'SELECT OFF'
                    else:
                        msg = 'Unknown'

                    # self.send_event(False, int(cmd, 16), int(data, 16), msg)
                    # if self.port_no2 > 0:
                    #     self.send_event(False, int(cmd, 16), int(data, 16), msg, self.port_no2)
                    for m in range(self.dual+1):
                        self.send_event(False, int(cmd, 16), int(data, 16), msg, cs=m)
                    msg = cmd + ':' + data + ':' + status + ' ' + msg

                elif cmd == '0071':
                    # port_status = self.port_status
                    # port_status2 = self.port_status2
                    port_status = [-1]*3
                    for n in range(3):
                        port_status[n] = self.port_status[n]
                    
                    if self.e84_dual == 2: # Dual mode
                        if data[2:4] == '00':
                            msg = 'IDLE'
                        elif data[2:4] == '01':
                            msg = 'Ready to Load'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Ready to Load'
                            self.clear_rfid()
                        elif data[2:4] == '02':
                            msg = 'Ready to Unload'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Ready to Unload'
                            self.read_rfid()
                        elif data[2:4] == '03':
                            # self.state['loading'] = True
                            # self.state['load_complete'] = False
                            msg = 'Load PS/PL Start'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Loading'
                        elif data[2:4] == '04':
                            # self.state['unloading'] = True
                            # self.state['unload_complete'] = False
                            msg = 'Unload PS/PL Start'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Unloading'
                        elif data[2:4] == '05':
                            # self.state['loading'] = False
                            # self.state['load_complete'] = True
                            msg = 'Load Complete'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Load Complete'
                            self.read_rfid()
                            
                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                            if settings.API_ENABLE:
                                json_data = {}
                                json_data['port_no'] = self.port_no[0]
                                json_data['Command'] = 'Load'
                                self.controller.api_svc.on_notify(json_data)
                        elif data[2:4] == '06':
                            # self.state['unloading'] = False
                            # self.state['unload_complete'] = True
                            msg = 'Unload Complete'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Unload Complete'
                            self.clear_rfid()
                                                        
                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                        elif data[2:4] == '07':
                            # print(f"auto recover status={status}")
                            # self.state['alarm'] = False
                            self.errorCode = 0
                            self.errorMsg = ''
                            # self.port_status = 0
                            # self.alarm_id = 0
                            # self.alarm_text = ''
                            m = int(status[0])
                            self.alarm_id[m] = 0
                            self.alarm_text[m] = ''
                            port_status[m] = int(data, 16)
                            msg = 'Alarm Solve (Right)' if m > 0 else 'Alarm Solve' # Auto Recover
                            self.port_status_msg[m] = msg
                            # port_status = int(data, 16)
                            # self.port_status_msg = 'Auto Recover'
                            # self.e84_cmd(last_error)

                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)
                                
                        elif data[2:4] == '08':
                            msg = f'PS{int(data[0:2], 16)} ON'
                        elif data[2:4] =='09':
                            msg = f'PS{int(data[0:2], 16)} OFF'
                        elif data[2:4] == '0a': # Dual mode
                            msg = f'PL{int(data[0:2], 16)} ON'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_read_rfid()
                        elif data[2:4] == '0b': # Dual mode
                            msg = f'PL{int(data[0:2], 16)} OFF'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_clear_rfid()
                        elif data[2:4] =='0c':
                            msg = 'CLAMP ON'
                        elif data[2:4] == '0d':
                            msg = 'CLAMP OFF'
                        elif data[2:4] == '0e':
                            msg = 'LIGHT ON'
                        elif data[2:4] == '0f':
                            msg = 'LIGHT OFF'
                        elif data[2:4] == '10':
                            msg = 'EQER ON'
                        elif data[2:4] == '11':
                            msg = 'EQER OFF'
                        elif data[2:4] == '12':
                            msg = 'CS0 Continue'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'CS0 Continue'
                        elif data[2:4] == '13':
                            msg = 'CS1 Continue'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'CS1 Continue'
                        elif data[2:4] == '14':
                            msg = 'Ready to Load (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Ready to Load (Right)'
                            self.clear_rfid(1)
                        elif data[2:4] == '15':
                            msg = 'Ready to Unload (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Ready to Unload (Right)'
                            self.read_rfid(1)
                        elif data[2:4] == '16':
                            msg = 'Load PS/PL Start (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Loading (Right)'
                        elif data[2:4] == '17':
                            msg = 'Unload PS/PL Start (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Unloading (Right)'
                        elif data[2:4] == '18':
                            msg = 'Load Complete (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Load Complete (Right)'
                            self.read_rfid(1)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)
                        elif data[2:4] == '19':
                            msg = 'Unload Complete (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Unload Complete (Right)'
                            self.clear_rfid(1)
                            
                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)
                        elif data[2:4] == '1a':
                            msg = f'PS{int(data[0:2], 16)} ON'
                        elif data[2:4] =='1b':
                            msg = f'PS{int(data[0:2], 16)} OFF'
                        elif data[2:4] == '1c':
                            msg = f'PL{int(data[0:2], 16)} ON'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_read_rfid()
                        elif data[2:4] == '1d':
                            msg = f'PL{int(data[0:2], 16)} OFF'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_clear_rfid()
                        elif data[2:4] == '1e':
                            msg = f'PS{int(data[0:2], 16)} ON (Right)'
                        elif data[2:4] =='1f':
                            msg = f'PS{int(data[0:2], 16)} OFF (Right)'
                        elif data[2:4] == '20':
                            msg = f'PL{int(data[0:2], 16)} ON (Right)'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_read_rfid(1)
                        elif data[2:4] == '21':
                            msg = f'PL{int(data[0:2], 16)} OFF (Right)'
                            if settings.PL_SENSOR_RFID_READ:
                                if data[0:2] == '00':
                                    self.manual_clear_rfid(1)
                        elif data[2:4] == '22':
                            msg = 'CS0 IDLE'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'CS0 IDLE'
                            # print(f"{self.port_no} {cmd}:{data} carrier_id : {self.rfid_data}")
                        elif data[2:4] == '23':
                            msg = 'CS1 IDLE'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'CS1 IDLE'
                            # print(f"{self.port_no2} {cmd}:{data} carrier_id : {self.rfid_data2}")
                        elif data[2:4] == '24':
                            msg = 'LIGHT ON (Right)'
                        elif data[2:4] == '25':
                            msg = 'LIGHT OFF (Right)'
                        elif data[2:4] == '26':
                            msg = 'CLAMP ON (Right)'
                        elif data[2:4] == '27':
                            msg = 'CLAMP OFF (Right)'
                        elif data[2:4] == '28':
                            msg = 'Software restart alarm reminder'
                        elif data[2:4] == '29':
                            msg = 'Software restart alarm reminder (Right)'
                        elif data[2:4] == '2a':
                            msg = 'Door Open ON'
                        elif data[2:4] == '2b':
                            msg = 'Door Open OFF'
                        elif data[2:4] == '2c':
                            msg = 'Door Close ON'
                        elif data[2:4] == '2d':
                            msg = 'Door Close OFF'
                        elif data[2:4] == '2e':
                            msg = 'Door Open ON (Right)'
                        elif data[2:4] == '2f':
                            msg = 'Door Open OFF (Right)'
                        elif data[2:4] == '30':
                            msg = 'Door Close ON (Right)'
                        elif data[2:4] == '31':
                            msg = 'Door Close OFF (Right)'
                        elif data[2:4] == '32':
                            msg = 'Relay ON'
                        elif data[2:4] == '33':
                            msg = 'Relay OFF'
                        elif data[2:4] == '34':
                            msg = 'Manual to Auto Refresh (Check PS PL Error)'
                        elif data[2:4] == '35':
                            msg = 'Manual to Auto Refresh (Check PS PL Error) (Right)'

                        else:
                            msg = 'Unknown'
                    else: # Single mode
                        if data == '0000':
                            msg = 'IDLE'
                        elif data == '0001':
                            msg = 'Ready to Load'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Ready to Load'
                            self.clear_rfid()
                        elif data == '0002':
                            msg = 'Ready to Unload'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Ready to Unload'
                            if settings.MULTIPLE_TYPE:
                                if not self.sensor_HRDD_FRSC['home']:
                                    self.read_rfid(1)
                                else:
                                    self.read_rfid()
                            else:
                                self.read_rfid()
                        elif data == '0003':
                            # self.state['loading'] = True
                            # self.state['load_complete'] = False
                            msg = 'Load PS/PL Start'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Loading'
                        elif data == '0004':
                            # self.state['unloading'] = True
                            # self.state['unload_complete'] = False
                            msg = 'Unload PS/PL Start'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Unloading'
                        elif data == '0005':
                            # self.state['loading'] = False
                            # self.state['load_complete'] = True
                            msg = 'Load Complete'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Load Complete'
                            if settings.MULTIPLE_TYPE:
                                if status == '10':
                                    self.read_rfid(1)
                                else:
                                    self.read_rfid()
                            else:
                                self.read_rfid()
                            
                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                            if settings.API_ENABLE:
                                json_data = {}
                                json_data['port_no'] = self.port_no[0]
                                json_data['Command'] = 'Load'
                                self.controller.api_svc.on_notify(json_data)
                        elif data == '0006':
                            # self.state['unloading'] = False
                            # self.state['unload_complete'] = True
                            msg = 'Unload Complete'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'Unload Complete'
                            self.clear_rfid()
                                                        
                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                        elif data == '0007':
                            # print(f"auto recover status={status}")
                            # self.state['alarm'] = False
                            self.errorCode = 0
                            self.errorMsg = ''
                            # self.port_status = 0
                            # self.alarm_id = 0
                            # self.alarm_text = ''
                            m = int(status[0])
                            self.alarm_id[m] = 0
                            self.alarm_text[m] = ''
                            port_status[m] = int(data, 16)
                            msg = 'Alarm Solve (Right)' if m > 0 else 'Alarm Solve' # Auto Recover
                            self.port_status_msg[m] = msg
                            # port_status = int(data, 16)
                            # self.port_status_msg = 'Auto Recover'
                            # self.e84_cmd(last_error)

                            if settings.DOOR:
                                self.e84_cmd(relay_off, True)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)

                        elif data == '0008': # Single mode
                            msg = 'PS ON'
                            if settings.MANUAL_MODE_PS_SENSOR_RFID_READ:
                                if self.mode[0] != 1: # not Auto mode
                                    self.manual_read_rfid()
                        elif data == '0009': # Single mode
                            msg = 'PS OFF'
                            if settings.MANUAL_MODE_PS_SENSOR_RFID_READ:
                                if self.mode[0] != 1: # not Auto mode
                                    self.manual_clear_rfid()
                        elif data == '000a': # Single mode
                            msg = 'PL ON'
                            if settings.PL_SENSOR_RFID_READ:
                                if self.mode[0] != 1: # not Auto mode
                                    self.manual_read_rfid()
                        elif data == '000b': # Single mode
                            msg = 'PL OFF'
                            if settings.PL_SENSOR_RFID_READ:
                                if self.mode[0] != 1: # not Auto mode
                                    self.manual_clear_rfid()
                        elif data == '0108':
                            msg = 'PS1 ON'
                        elif data == '0208':
                            msg = 'PS2 ON'
                        elif data == '0308':
                            msg = 'PS3 ON'
                        elif data == '0408':
                            msg = 'PS4 ON'
                        elif data == '0508':
                            msg = 'PS5 ON'
                        elif data == '0608':
                            msg = 'PS6 ON'
                        elif data == '0708':
                            msg = 'PS7 ON'
                        elif data == '0808':
                            msg = 'PS8 ON'
                        elif data =='0109':
                            msg = 'PS1 OFF'
                        elif data =='0209':
                            msg = 'PS2 OFF'
                        elif data =='0309':
                            msg = 'PS3 OFF'
                        elif data =='0409':
                            msg = 'PS4 OFF'
                        elif data =='0509':
                            msg = 'PS5 OFF'
                        elif data =='0609':
                            msg = 'PS6 OFF'
                        elif data =='0709':
                            msg = 'PS7 OFF'
                        elif data =='0809':
                            msg = 'PS8 OFF'
                        elif data == '010a':
                            msg = 'PL1 ON'
                        elif data == '020a':
                            msg = 'PL2 ON'
                        elif data == '030a':
                            msg = 'PL3 ON'
                        elif data == '040a':
                            msg = 'PL4 ON'
                        elif data == '050a':
                            msg = 'PL5 ON'
                        elif data == '060a':
                            msg = 'PL6 ON'
                        elif data == '070a':
                            msg = 'PL7 ON'
                        elif data == '080a':
                            msg = 'PL8 ON'
                        elif data == '010b':
                            msg = 'PL1 OFF'
                        elif data == '020b':
                            msg = 'PL2 OFF'
                        elif data == '030b':
                            msg = 'PL3 OFF'
                        elif data == '040b':
                            msg = 'PL4 OFF'
                        elif data == '050b':
                            msg = 'PL5 OFF'
                        elif data == '060b':
                            msg = 'PL6 OFF'
                        elif data == '070b':
                            msg = 'PL7 OFF'
                        elif data == '080b':
                            msg = 'PL8 OFF'
                        elif data =='000c':
                            msg = 'CLAMP ON'
                        elif data == '000d':
                            msg = 'CLAMP OFF'
                        elif data == '000e':
                            msg = 'LIGHT ON'
                        elif data == '000f':
                            msg = 'LIGHT OFF'
                        elif data == '0010':
                            msg = 'EQ_ER ON'
                        elif data == '0011':
                            msg = 'EQER OFF'
                        elif data == '0012':
                            msg = 'CS0 Continue'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'CS0 Continue'
                        elif data == '0013':
                            msg = 'CS1 Continue'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'CS1 Continue'
                        elif data == '0014':
                            msg = 'Ready to Load (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Ready to Load (Right)'
                            self.clear_rfid(1)
                        elif data == '0015':
                            msg = 'Ready to Unload (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Ready to Unload (Right)'
                            self.read_rfid(1)
                        elif data == '0016':
                            msg = 'Load PS/PL Start (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Loading (Right)'
                        elif data == '0017':
                            msg = 'Unload PS/PL Start (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Unloading (Right)'
                        elif data == '0018':
                            msg = 'Load Complete (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Load Complete (Right)'
                            self.read_rfid(1)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)
                        elif data == '0019':
                            msg = 'Unload Complete (Right)'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'Unload Complete (Right)'
                            self.clear_rfid(1)

                            if settings.LED_ENABLE:
                                self.controller.led_controller.turn_off_channel(self.led_id, timeout=1.5)
                        elif data == '001a':
                            msg = 'PS ON Left'
                        elif data =='001b':
                            msg = 'PS OFF Left'
                        elif data == '001c':
                            msg = 'PL ON Left'
                        elif data == '001d':
                            msg = 'PL OFF Left'
                        elif data == '001e':
                            msg = 'PS ON Right'
                        elif data =='001f':
                            msg = 'PS OFF Right'
                        elif data == '0020':
                            msg = 'PL ON Right'
                        elif data == '0021':
                            msg = 'PL OFF Right' 
                        elif data == '0022':
                            msg = 'CS0 IDLE'
                            port_status[0] = int(data, 16)
                            self.port_status_msg[0] = 'CS0 IDLE'
                            # print(f"{self.port_no} {cmd}:{data} carrier_id : {self.rfid_data}")
                        elif data == '0023':
                            msg = 'CS1 IDLE'
                            port_status[1] = int(data, 16)
                            self.port_status_msg[1] = 'CS1 IDLE'
                            # print(f"{self.port_no2} {cmd}:{data} carrier_id : {self.rfid_data2}")
                        elif data == '0024':
                            msg = 'LIGHT ON Right'
                        elif data == '0025':
                            msg = 'LIGHT OFF Right'
                        elif data == '0026':
                            msg = 'CLAMP ON Right'
                        elif data == '0027':
                            msg = 'CLAMP OFF Right'
                        elif data == '0028':
                            msg = 'Software restart alarm reminder'
                        elif data == '0029':
                            msg = 'Software restart alarm reminder Right'
                        elif data == '002a':
                            msg = 'Door Open ON'
                        elif data == '002b':
                            msg = 'Door Open OFF'
                        elif data == '002c':
                            msg = 'Door Close ON'
                        elif data == '002d':
                            msg = 'Door Close OFF'
                        elif data =='002e':
                            msg = 'Relay ON'
                        elif data == '002f':
                            msg = 'Relay OFF'
                        elif data == '0031':
                            msg = 'IO Ready ON'
                        elif data == '0032':
                            msg = 'IO Ready OFF'
                        elif data == '0033':
                            msg = 'IO Busy ON'
                        elif data == '0034':
                            msg = 'IO Busy OFF'
                        elif data == '0035':
                            msg = 'IO Checking ON'
                        elif data == '0036':
                            msg = 'IO Checking OFF'
                        elif data == '0037':
                            msg = 'IO Home ON'
                            if settings.MULTIPLE_TYPE:
                                if self.port_status[0] != 5:
                                    self.e84_cmd(inch12_off, True)
                        elif data == '0038':
                            msg = 'IO Home OFF'
                            if settings.MULTIPLE_TYPE:
                                if self.port_status[0] != 5:
                                    self.e84_cmd(inch12_on, True)
                        elif data == '0039':
                            msg = 'IO Lock ON'
                        elif data == '003a':
                            msg = 'IO Lock OFF'
                        elif data == '003b':
                            msg = 'IO Latch1 ON'
                        elif data == '003c':
                            msg = 'IO Latch1 OFF'
                        elif data == '003d':
                            msg = 'IO Latch2 ON'
                        elif data == '003e':
                            msg = 'IO Latch2 OFF'
                        elif data == '003f':
                            msg = 'IO Move ON'
                        elif data == '0040':
                            msg = 'IO Move OFF'
                        # elif data == '0012':
                        #     msg = 'Right load complete'
                        #     print(f"{self.port_id} {cmd}:{data} carrier_id : {self.rfid_data}")
                        # elif data == '0013':
                        #     msg = 'Right unload complete'
                        #     print(f"{self.port_id} {cmd}:{data} carrier_id : {self.rfid_data}")
                        # elif data == '0014':
                        #     # self.state['unloading'] = False
                        #     # self.state['unload_complete'] = True
                        #     msg = 'cs0 continue'
                        # elif data == '0015':
                        #     msg = 'cs1 continue'
                        else:
                            msg = 'Unknown'

                    if data[0] == '0':
                        for m in range(self.dual+1):
                            self.load[m] = int(data, 16) # 0071 status
                    else:
                        # print(f"data[0] = {int(data[0])}")
                        m = int(data[0]) - 1
                        if m <= 2: # only support CS1, CS2
                            self.load[m] = int(data, 16)
                    
                    bSend = False
                    # if self.port_status != port_status :
                    #     self.port_status = port_status
                    #     self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg, 0)
                    #     bSend = True
                        
                    # if self.port_status2 != port_status2 :
                    #     self.port_status2 = port_status2
                    #     self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg2, 1)
                    #     bSend = True
                    for m in range(self.dual+1):
                        if self.port_status[m] != port_status[m] :
                            self.port_status[m] = port_status[m]
                            self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg[m], cs=m)
                            bSend = True
                        
                    if not bSend:
                        # self.send_event(False, int(cmd, 16), int(data, 16), msg)
                        # if self.port_no2 > 0:
                        #     self.send_event(server=False, code=int(cmd, 16), subcode=int(data, 16), msg_text=msg, dual=self.port_no2)
                        for m in range(self.dual+1):
                            self.send_event(server=False, code=int(cmd, 16), subcode=int(data, 16), msg_text=msg, cs=m)
                    
                    msg = cmd + ':' + data + ':' + status + ' ' + msg

                elif cmd == '0080':
                    # self.state['alarm'] = True
                    self.errorCode = data
                    # self.errorMsg = e84_errorCode.get(data, '')
                    # msg = e84_errorCode.get(data, '')
                    #print('err:', data, msg)
                    # if self.port_status != port_status :
                    # self.port_status = 6

                    try:
                        m = int(status[0])
                        self.alarm_id[m] = int(data, 16)
                        self.alarm_text[m] = self.alarm_msg(data, m)
                        self.send_event(True, int(cmd, 16), self.alarm_id[m], self.alarm_text[m], cs=m)
                        msg = cmd + ':' + data + ':' + status + f" Alarm : {self.alarm_id[m]}, {self.alarm_text[m]}"
                        self.logger.info(f"{self.port_id[m]} {msg}")
                        
                        # self.alarm_text = e84_err_code[int(data, 16)]
                        # self.send_event(True, int(cmd, 16), int(data, 16), self.alarm_text)
                        
                        # self.alarm_text = ftp_alarmlist['S05F01'][128][self.alarm_id]['msgtext']
                        # self.send_event(True, int(cmd, 16), self.alarm_id, self.alarm_text)
                        # if self.port_no2 > 0:
                        #     self.send_event(server=True, code=int(cmd, 16), subcode=self.alarm_id, msg_text=self.alarm_text, dual=self.port_no2)
                    except Exception as err:
                        self.logger.error(str(err))
                        # self.alarm_text = 'Alarm code not in database list'
                        # self.send_event(True, int(cmd, 16), self.alarm_id, self.alarm_text)
                        # if self.port_no2 > 0:
                        #     self.send_event(server=True, code=int(cmd, 16), subcode=self.alarm_id, msg_text=self.alarm_text, dual=self.port_no2)
                        
                    continue
                else:
                    # self.send_event(True, int(cmd,16), int(data,16), 'Unknown cmd')
                    # if self.port_no2 > 0:
                    #         self.send_event(server=True, code=int(cmd, 16), subcode=int(data,16), msg_text='Unknown cmd', dual=self.port_no2)
                    for m in range(self.dual+1):
                        self.send_event(server=True, code=int(cmd, 16), subcode=int(data,16), msg_text='Unknown cmd', cs=m)
                    msg = cmd + ':' + data + ':' + status + " Unknown cmd"

                if len(self.response_queue) > 0:
                    if self.response_queue[0]['cmd'] == int(cmd, 16):
                        res = self.response_queue.popleft()
                        self.mqtt_publish_response(res['cmd'], msg, res['props'])

                if msg:
                    if cmd == '0070' and not settings.LOG_0070 :
                        continue
                    if cmd == '0071' and not settings.LOG_0071 :
                        continue
                    # tmp = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
                    # print(f"{tmp} {self.port_id} {msg}")
                    # self.logger.info(f"{tmp} {self.port_id} {msg}")
                    m = int(status[0])
                    self.logger.info(f"{self.port_id[m]} {msg}")

                # log
                # if self.logger:
                #     logMsg = '{} {}, {}'.format(cmd, data, msg)
                #     if cmd != '0080':
                #         self.logger.bashLog('INFO', logMsg)
                #     else:
                #         self.logger.bashLog('ERROR', logMsg)
                #     time.sleep(0.1)
            except:
                traceback.print_exc()
                # self.check()
                if self.e84 != None:
                    self.e84.stop()
                #logger.error(traceback.format_exc())
                time.sleep(3)
