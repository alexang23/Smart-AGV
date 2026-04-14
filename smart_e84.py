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
initial =   (0x55, 0xAA, 0x00, 0x24, 0x00, 0x01)
version =   (0x55, 0xAA, 0x00, 0x00, 0x00, 0x00)
version2 =  (0x55, 0xAA, 0x00, 0x01, 0x00, 0x00)
reset =     (0x55, 0xAA, 0x80, 0x02, 0x00, 0x00)
reset2 =    (0x55, 0xAA, 0x80, 0x02, 0x00, 0x00)
read_mode =    (0x55, 0xAA, 0x00, 0x03, 0x00, 0x00)
manual =    (0x55, 0xAA, 0x80, 0x03, 0x00, 0x00)
manual2 =   (0x55, 0xAA, 0x80, 0x03, 0x00, 0x00)
auto =      (0x55, 0xAA, 0x80, 0x03, 0x00, 0x01)
auto2 =     (0x55, 0xAA, 0x80, 0x03, 0x00, 0x02)

ps_on = (0x55, 0xAA, 0x80, 0x19, 0x00, 0xFF)
ps_off = (0x55, 0xAA, 0x80, 0x19, 0x00, 0x00)
clamp_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x03)
light_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x05)
eqer_on = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x09)
clamp_off = (0x55, 0xAA, 0x80, 0x16, 0x00, 0x01)
check_light_on = (0x55, 0xAA, 0x81, 0x23, 0x00, 0x01)
check_light_off = (0x55, 0xAA, 0x81, 0x23, 0x00, 0x00)
enable0070 = (0x55, 0xAA, 0x80, 0x13, 0x55, 0xAA)

            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x03)) # simulation mode clamp on
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x01)) # simulation mode clamp off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x00)) # simulation mode ps off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x01)) # simulation mode ps on


link = (0x55, 0xAA, 0x00, 0x52, 0x00, 0x00)

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
pspl =        (0x55, 0xAA, 0x00, 0x19, 0x00, 0x00) # 25 LED_PSPL
                                    # this.eapport_0.LED_PSPL[int_5] = int_7;
                                    # int int_9 = (this.eapport_0.LED_PSPL[int_5] & 31) | (this.eapport_0.LED_DONE[int_5] & 3) << 6 | (this.eapport_0.LED_EXTIO[int_5] & 16) << 3;
                                    # this.method_9(int_5, 2, int_9);
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

cmd80 = {
0x001 : 'Port Open',
0x002 : 'Reset',
0x003 : 'Set Load/Unload',
0x004 : 'ARM Back Completed',
0x006 : 'Set CS',
0x008 : 'Set Continue',
0x010 : 'E84 Output Sensor',
0x011 : 'E84 Input Sensor',
0x012 : 'Power, Select, Mode, Go',
0x013 : 'cmd 0x70 ON/OFF',
0x022 : 'Not Alarm ON/OFF',
0x030 : 'Port ON/OFF',
0x040 : 'Set TA1 timeout',
0x041 : 'Set TA2 timeout',
0x042 : 'Set TA3 timeout',
0x043 : 'Set TA4 timeout',
0x044 : 'Set TA5 timeout',
0x045 : 'Set TA6 timeout',
0x049 : 'Read Error Code',
0x04a : 'Timeout Enable',
0x04b : 'Timeout Timer',
0x04c : 'Link connected signal report',
0x04d : 'Set DB25 Input Debounce Time',
0x04e : 'Set TA7 timeout',
0x04f : 'Set TA8 timeout',
0x050 : 'Set TA9 timeout',
0x051 : 'Set TA10 timeout',
0x052 : 'Set TA11 timeout',
0x053 : 'Set TA12 timeout',
0x054 : 'Set TA13 timeout',
0x055 : 'Set TA14 timeout',
0x056 : 'Set TA15 timeout',
0x057 : 'Set TA16 timeout',
0x060 : 'Simulation Startup',
0x061 : 'Simulation E84 Input',
0x065 : 'HW Port Select Set',
0x067 : 'Set TD0 timeout',
}

event71 = {
0x0001 : 'Ready to Handoff',
0x0002 : 'Loading', # ARM can Load
0x0003 : 'Load Complete',
0x0004 : 'Handoff Complete',
0x1002 : 'Unloading', # 4098 ARM can Unload
0x1003 : 'Unload Complete', # 4099
0x1004 : 'Charge Command ON',
0x1005 : 'Charge Command OFF',
0x1006 : 'Request Free ON',
0x1007 : 'Request Free OFF',
0x1008 : 'Coupler HP ON',
0x1009 : 'Coupler HP OFF',
0x100a : 'Charge Error ON',
0x100b : 'Charge Error OFF',
0x100c : 'Full Charge ON',
0x100d : 'Full Charge OFF',
0x100e : 'Coupler OP ON',
0x100f : 'Coupler OP OFF',
}


alarm80 = {
0x009 : '0x00 : CS0 IDLE Light Curtain ON',
0x002 : '0x00 : CS0 Ready To Idle PS OFF',
0x003 : '0x00 : CS0 Ready To Idle PS ON',
0x004 : '0x00 : CS0 Ready To Idle PL OFF',
0x005 : '0x00 : CS0 Ready To Idle PL ON',
0x00D : '0x00 : CS0 BOX OPEN ON in IDLE mode',
0x00F : '0x00 : CS0 BOX CLOSE ON in IDLE mode',
0x207 : '0x00 : CS0 Handshake Clamp ON in IDLE mode',
0x20A : '0x00 : CS0 Handsshake BOX OFF in IDLE mode',
0x20C : '0x00 : CS0 Handshake BOX CLOSE OFF in IDLE mode',
0x402 : '0x00 : CS0 Ready To Unload PS OFF',
0x404 : '0x00 : CS0 Ready To Unload PL OFF',
0x602 : '0x00 : CS0 Handshake To Unload PS OFF',
0x603 : '0x00 : CS0 Handshake To Unload PS ON',
0x604 : '0x00 : CS0 Handshake To Unload PL OFF',
0x605 : '0x00 : CS0 Handshake To Unload PL ON',
0x611 : '0x00 : CS0 Handshake To Unload Input Only ON',
0x614 : '0x00 : CS0 Handshake To Unload Door Open OFF',
0x803 : '0x00 : CS0 Ready To Load PS ON',
0x805 : '0x00 : CS0 Ready To Load PL ON',
0xA03 : '0x00 : CS0 Handshake To Load PS ON',
0xA07 : '0x00 : CS0 Handshake To Load Clamp ON',
0xA13 : '0x00 : CS0 Handshake To Load Output Only ON',
0xA14 : '0x00 : CS0 Handshake To Load Door Open OFF',
0x6F1 : '0x00 : CS0 Handshake to Unload TD0 Timeout',
0x6F3 : '0x00 : CS0 Handshake to Unload TP1 Timeout',
0x6F5 : '0x00 : CS0 Handshake to Unload TP2 Timeout',
0x6F7 : '0x05 : CS0 Handshake to Unload TP3 Timeout',
0x6F9 : '0x00 : CS0 Handshake to Unload TP4 Timeout',
0x6FB : '0x00 : CS0 Handshake to Unload TP5 Timeout',
0x6FD : '0x00 : CS0 Handshake to Unload TP6 Timeout',
0xAF1 : '0x00 : CS0 Handshake to Load TD0 Timeout',
0xAF3 : '0x00 : CS0 Handshake to Load TP1 Timeout',
0xAF5 : '0x00 : CS0 Handshake to Load TP2 Timeout',
0xAF7 : '0x05 : CS0 Handshake to Load TP3 Timeout',
0xAF9 : '0x00 : CS0 Handshake to Load TP4 Timeout',
0xAFB : '0x00 : CS0 Handshake to Load TP5 Timeout',
0xAFD : '0x00 : CS0 Handshake to Load TP6 Timeout',    
}

alarm01 = {
1 : 'CS0',
2 : 'CS1',
3 : 'CS2',
4 : 'CS3',
5 : 'CS4',
6 : 'CS5',
7 : 'CS6',
}

alarm02 = {
0 : 'Idle',
1 : 'Unload',
2 : 'Load',
}

alarm03 = {
0 : ' mode',
1 : ' Power ON',
2 : 'ing',
}

alarm04 = {
1 : 'PS',
2 : 'PL',
3 : 'Clamp',
4 : 'Light Curtain',
5 : 'Box',
6 : 'Box Open',
7 : 'Box Close',
8 : 'Input Only',
9 : 'Output Only',
10 : 'Manual',
11 : 'Cassette',
12 : 'Door1',
13 : 'Door2',
100 : 'L_REQ',
101 : 'U_REQ',
102 : 'VA',
103 : 'READY',
104 : 'VS0',
105 : 'VS1',
106 : 'HO_AVBL',
107 : 'ES',
108 : 'VALID',
109 : 'CS0',
110 : 'CS1',
111 : 'AM_AVBL',
112 : 'TR_REQ',
113 : 'BUSY',
114 : 'CONT',
115 : 'GO',
120 : 'TD0 Timeout',
121 : 'TP1 Timeout',
122 : 'TP2 Timeout',
123 : 'TP3 Timeout',
124 : 'TP4 Timeout',
125 : 'TP5 Timeout',
126 : 'TP6 Timeout',
}

alarm05 = {
0 : 'OFF',
1 : 'ON',
}

alarm06 = {
0 : 'TA1 Timeout',
1 : 'TD0 Timeout',
3 : 'TP1 Timeout',
5 : 'TP2 Timeout',
7 : 'TP3 Timeout',
9 : 'TP4 Timeout',
0xB : 'TP5 Timeout',
0xD : 'TP6 Timeout',
0xE : 'TA2 Timeout',
0xF : 'TA3 Timeout',
}

class SmartE84(threading.Thread):
    def __init__(self, devPath, controller=None, log=None, enable=True, port_no=1, port_id='LP1', rfid=None, event_mgr=None, max_queue_size=1000):
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
        self.event_mgr = event_mgr

        self.power = 0
        self.load_function = 0

        # self.port_id = port_id
        # self.port_id2 = None
        self.port_id = [port_no] + [-1] * (settings.CS_NUMBER - 1)
        self.message = ''
        # self.port_no = port_no
        # self.port_no2 = -1
        self.port_no = [port_no] + [-1] * (settings.CS_NUMBER - 1)
        self.mode_bit = 0
        # self.mode = 0
        # self.mode2 = 0
        self.mode = [0] * (settings.CS_NUMBER)
        # self.port_status = 0
        # self.port_status2 = 0
        self.port_status = [0] * (settings.CS_NUMBER)
        self.safety = -1
        self.pspl = -1
        self.dual = 0
        # self.load = -1
        # self.load2 = -1
        self.load = [-1] * (settings.CS_NUMBER)
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
        self.port_status_msg = ['Out of Service'] * (settings.CS_NUMBER)
        self.port_connected = 0
        
        self.sensor_elce = -1
        self.pspl_usage = -1
        self.pspl_setting = -1
        self.e84_out = -1
        self.e84_in = -1
        self.e84_smg = -1

        # self.alarm_id = 0
        # self.alarm_id2 = 0
        self.alarm_id = [0] * (settings.CS_NUMBER)
        # self.alarm_text = ''
        # self.alarm_text2 = ''
        self.alarm_text = [''] * (settings.CS_NUMBER)

        self.rfid_type = 0
        self.rfid_port = 0
        self.rfid_dual = 0
        self.rfid_page = 1
        # self.rfid_data = None
        # self.rfid_data2 = None
        self.rfid_data = [None] * (settings.CS_NUMBER)
        self.clamp = False
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
            self.e84 = E84Client(self.devPath, f"COM{settings.E84_RF_SENSOR_COM}", baudrate=115200, on_message_event=self.e84_message, on_sensor_event=self.quick_monitor, on_alarm_event=self.on_alarm, event_queue_size=100)
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
        # 20260127 SmartIO-AGV
        # print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [######## 即時 E84 message] {data.hex()}")
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
        # print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [即時] {signal}: {'ON' if state else 'OFF'}")
        pass

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
        data['mode'] = self.mode
        data['carrier_id'] = self.rfid_data
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
            data['version'] = f"{self.fw_version}"
            self.event_mgr.on_notify(data)
            
        except Exception as err:
            self.logger.info(str(err))

    def send_event2(self, server=False, stream=-1, function=-1, code=-1, subcode=-1, msg_text=None, cs=0):
        try:
            data = OrderedDict()
            
            if server:
                data['Server'] = True
                
            data['device_id'] = self.controller.device_id
            data['port_no'] = self.port_no[cs]
            data['port_id'] = self.port_id[cs]
            data['port_state'] = self.port_status[cs]
            data['carrier_id'] = self.rfid_data[cs]
            data['dual_port'] = cs
            data['mode'] = self.mode[cs] # Access Mode 0: Unknown, 1: Auto, 2: Manual
            data['load'] = self.load[cs]  # 0071 status
            data['alarm_id'] = self.alarm_id[cs]
            data['alarm_text'] = self.alarm_text[cs]
            data['type'] = 0
            data['stream'] = stream
            data['function'] = function
            data['code_id'] = code
            data['sub_id'] = subcode
            data['msg_text'] = msg_text
            data['status'] = ''
            data['occurred_at'] = time.time()
            data['version'] = f"{self.fw_version}"
            self.event_mgr.on_notify(data)
        except Exception as err:
            self.logger.info(str(err))

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

    def e84_cmd(self, data):
        # SmartIO-AGV comment out
        return

        if self.e84 == None:
            return
            
        data = list(data)
        data.append(sum(data)%256)
        # self.e84_queue.append(struct.pack('>BBBBBBB', *data))
        # #e84.write(struct.pack('>BBBBBBB', *data))
        self.e84.write(struct.pack('>BBBBBBB', *data))

    def run_cmd2(self, cs, cmd, data):
        
        if self.e84 == None:
            return
        
        cmd2 = '55aa' + cmd + data
        cmd3 = bytes.fromhex(cmd2)
        # print(list(cmd3))
        # print(hex(int(cmd2, 16)))
        print(f"cmd=0x{int(cmd, 16):04X}, data=0x{int(data, 16):04X}")
        
        self.e84_cmd(cmd3)

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
            self.e84_cmd(initial)

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
                    for m in range(self.dual+1):
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

        self.e84_cmd(last_error)
        # self.e84_cmd(link) # don't get any response
        # self.e84_cmd(test2)

        # self.e84_cmd(version)   # check e84 is connecting
        self.e84_cmd(e84_out) 
        self.e84_cmd(e84_in)
        self.e84_cmd(e84_smg)
        self.e84_cmd(pspl)
        self.e84_cmd(mode_state)
        self.e84_cmd(sensor_elce)
        self.e84_cmd(test3)
        self.e84_cmd(test4)
        self.e84_cmd(test5)
        # self.e84_cmd(link_reset)

        # self.e84_cmd(sensor_use)
        # self.e84_cmd(sensor_set)
        # self.e84_cmd(mode)
        
    def send_status(self):
        for m in range(self.dual+1):
            self.send_event2(server=True, stream=6, function=11, code=0, subcode=0, msg_text=self.port_status_msg, cs=m)

    def api_request(self, cmd, data, props):
        
        if self.e84 == None:
            return
        req = OrderedDict()
        req['cmd'] = cmd
        req['props'] = props
        if cmd == 32770: # alarm reset
            self.response_queue.append(req)
            self.e84_cmd(reset)
        elif cmd == 32771: # change mode
            if data == 1:
                self.response_queue.append(req)
                self.e84_cmd(auto)
            elif data == 2:
                self.response_queue.append(req)
                self.e84_cmd(manual)
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
            
            if cmd == 'initial':
                self.e84_cmd(initial)
            elif cmd == 'reset':
                self.e84_cmd(reset)
            elif cmd == 'reset2':
                self.e84_cmd(reset2)
            # elif cmd == 'auto':
            elif cmd.find('auto') >= 0:
                port_no = int(cmd.split(';')[1])
                self.e84_cmd(self.set_mode(port_no, 1))
            # elif cmd == 'auto2':
            #     self.e84_cmd(self.set_mode(self.port_no2, 1))
            # elif cmd == 'manual':
            elif cmd.find('manual') >= 0:
                port_no = int(cmd.split(';')[1])
                self.e84_cmd(self.set_mode(port_no, 0))
            # elif cmd == 'manual2':
            #     self.e84_cmd(self.set_mode(self.port_no2, 0))
            elif cmd == 'ps_on':
                self.e84_cmd(ps_on)
            elif cmd == 'ps_off':
                self.e84_cmd(ps_off)
            elif cmd == 'clamp_on':
                self.e84_cmd(clamp_on)
            elif cmd == 'clamp_off':
                self.e84_cmd(clamp_off)
            elif cmd == 'light_on':
                self.e84_cmd(light_on)
            elif cmd == 'light_off':
                self.e84_cmd(clamp_off)
            elif cmd == 'eqer_on':
                self.e84_cmd(eqer_on)
            elif cmd == 'eqer_off':
                self.e84_cmd(clamp_off)
            elif cmd == 'last_error':
                self.e84_cmd(last_error)
            elif cmd == 'check_light_on':
                self.e84_cmd(check_light_on)
            elif cmd == 'check_light_off':
                self.e84_cmd(check_light_off)
            elif cmd == 'version':
                self.e84_cmd(version)
            elif cmd == 'mode':
                self.e84_cmd(mode_state)
            elif cmd == 'status':
                self.send_status()
            elif cmd == 'alarm_reset':
                print('run_cmd : alarm_reset')
                self._run_coro(self.alarm_reset_async())
            elif cmd.find('alarm') >= 0:
                alarm_id = cmd.split()[1]
                self.send_alarm(alarm_id)
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
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before get_running_loop")
            loop = asyncio.get_running_loop()
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After get_running_loop succeeded")
        except RuntimeError:
            loop = None
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ loop is None")
        
        if loop and loop.is_running():
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before create_task")
            try:
                loop.create_task(coro)
                # 20260127 SmartIO-AGV
                # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After create_task succeeded")
            except Exception as err:
                # fallback: try thread-safe submission, or as last resort run in new loop
                # 20260127 SmartIO-AGV
                # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ create_task failed, falling back:", err)
                try:
                    asyncio.run_coroutine_threadsafe(coro, loop)
                except Exception:
                    # 20260127 SmartIO-AGV
                    # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ create_task failed again, falling back to new loop")
                    asyncio.run(coro)
        else:
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Before use asyncio.run")
            asyncio.run(coro)
            # 20260127 SmartIO-AGV
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ After use asyncio.run succeeded")

    async def _task_runner(self, coro_func, name, *args, **kwargs):
        """Run coro_func in a loop and restart it if it raises (logs traceback)."""
        while True:
            try:
                # 20260127 SmartIO-AGV
                # print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT Before await coro_func")
                await coro_func(*args, **kwargs)
                # 20260127 SmartIO-AGV
                # print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT After await coro_func")
            except asyncio.CancelledError:
                # Allow cancellation to propagate
                # 20260127 SmartIO-AGV
                # print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT await coro_func CancelledError")
                raise
            except Exception as err:
                # 20260127 SmartIO-AGV
                # self.logger.error(f"TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT {name} crashed: {err}\n{traceback.format_exc()}")
                # wait a bit before restarting
                await asyncio.sleep(1)
                continue
            break

    async def open_RF_channel(self):
        if self.e84 == None:
            return
        if self.e84._state.value != "connected":
            connected = False
            for attempt in range(1, 4):
                self.logger.info(f"open_RF_channel connect attempt {attempt}/3")
                await self.e84.connect_async()
                if self.e84._state.value == "connected":
                    connected = True
                    break
                if attempt < 3:
                    await asyncio.sleep(1)
            if not connected:
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
        # 20260127 SmartIO-AGV
        # print(f"######################## cs_async 結果: {'成功' if success else '失敗'} ########################")

    async def task_async(self, task: int = 0):
        if self.e84 == None:
            return
        if task == 0:
            success = await self.e84.cobot_load_async()
            # 20260127 SmartIO-AGV
            # print(f"######################## load_async 結果: {'成功' if success else '失敗'} ########################")
        else:
            success = await self.e84.cobot_unload_async()
            # 20260127 SmartIO-AGV
            # print(f"######################## unload_async 結果: {'成功' if success else '失敗'} ########################")

    async def handoff_async(self, cs: int = 0, task: int = 0):
        if self.e84 == None:
            return

        if self.e84._state.value != "connected":
            connected = False
            for attempt in range(1, 4):
                self.logger.info(f"handoff_async connect attempt {attempt}/3")
                await self.e84.connect_async()
                if self.e84._state.value == "connected":
                    connected = True
                    break
                if attempt < 3:
                    await asyncio.sleep(1)
            if not connected:
                print("❌ 連線失敗，可能原因：")
                print("   1. 串口不存在或已被占用")
                print("   2. 串口權限不足")
                print("   3. 波特率不正確")
                return
        
        success = await self.e84.cobot_cs_async(cs)
        # 20260127 SmartIO-AGV
        # print(f"######################## cs_async 結果: {'成功' if success else '失敗'} ########################")

        if task == 0:
            success = await self.e84.cobot_load_async()
            # 20260127 SmartIO-AGV
            # print(f"######################## load_async 結果: {'成功' if success else '失敗'} ########################")
        else:
            success = await self.e84.cobot_unload_async()
            # 20260127 SmartIO-AGV
            # print(f"######################## unload_async 結果: {'成功' if success else '失敗'} ########################")

    async def arm_back_async(self):
        if self.e84 == None:
            return False
        success = await self.e84.cobot_arm_back_complete_async()
        # print(f"######################## arm_back_complete_async 結果: {'成功' if success else '失敗'} ########################")
        return success

    async def _ensure_e84_connected(self, operation_name: str, attempts: int = 3):
        if self.e84 == None:
            return False

        if self.e84._state.value == "connected":
            return True

        for attempt in range(1, attempts + 1):
            self.logger.info(f"{operation_name} connect attempt {attempt}/{attempts}")
            try:
                await self.e84.connect_async()
            except Exception as err:
                self.logger.error(f"{operation_name} connect attempt {attempt}/{attempts} failed: {err}")

            if self.e84._state.value == "connected":
                return True

            if attempt < attempts:
                await asyncio.sleep(1)

        self.logger.error(f"{operation_name} failed: E84 client is not connected")
        return False

    async def alarm_reset_async(self):
        if self.e84 == None:
            return False

        if not await self._ensure_e84_connected("alarm_reset_async"):
            return False

        success = await self.e84.alarm_reset()
        # print(f"######################## alarm_reset_async 結果: {'成功' if success else '失敗'} ########################")
        return success

    def cmd_msg(self, data):
        try:
            cmd_msg = list(cmd80[int(data[1:],16)])
            return f"{''.join(cmd_msg)}"
        except Exception as err:
            self.logger.error(str(err))
            return f"0x{data}"

    def event_msg(self, data, cs=0):
        try:
            # event_msg = list(event71[int(data[1:],16)])
            # if data[0] != '0':
            #     event_msg[2] = str(cs)
            event_msg = list(event71[int(data,16)])
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

    def run(self):

        try:
            # schedule.every(10).seconds.do(self.check_connection)
            # schedule.every(1).seconds.do(self.update_state)
            # if self.rfid:
            #     schedule.every(1).seconds.do(self.update_rfid_data)
            if settings.CLAMP_TEST:
                schedule.every(3).seconds.do(self.clamp_test)
            if settings.MEMORY_CHECK:
                schedule.every(5).minutes.do(self.memory_check)

            # schedule.every(10).seconds.do(self.send_status)
            
            # self.e84 = serial.Serial(self.devPath, 115200, 8, 'N', 1, timeout=0.25)
            # self.e84.flushInput()
            # self.e84.reset_input_buffer()
            # self.e84_cmd(reset)
            # self.e84_cmd(auto)
            if self.enable:
                self.connect_serial_port()
            
            if self.e84 != None:
                # self.e84_cmd(link_reset)
                # self.e84_cmd(enable0070)
                # self.e84_cmd(reset)
                # self.e84_cmd(auto)
                # if self.dual:
                #     self.e84_cmd(reset2)
                #     self.e84_cmd(auto2)
                pass
                # self.e84_cmd(mode_state)
                
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x03)) # simulation mode clamp on
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x14, 0x00, 0x01)) # simulation mode clamp off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x00)) # simulation mode ps off
            #self.e84_cmd((0x55, 0xAA, 0x80, 0x17, 0x00, 0x01)) # simulation mode ps on

        except:
            traceback.print_exc()
            #logger.error('e84 initial connect fail')

        while not self.stop:
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
                                # self.e84_cmd(link_reset)
                                # self.e84_cmd(enable0070)
                                # # self.e84_cmd(reset)
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
                #                 # # self.e84_cmd(link_reset)
                #                 # self.e84_cmd(enable0070)
                #                 # # self.e84_cmd(reset)
                #                 # # self.e84_cmd(auto)
                #                 # # if self.dual:
                #                 # #     self.e84_cmd(auto2)
                #                 self.lastTime = time.time()
                #                 self.logger.info(f"{self.port_id[0]} daily reconnect COM port")
                #                 self.daily_reconnect = False
                #                 self.daily_reconnect_time = datetime.now()
                    
                if (not self.enable) and self.e84:
                    self.disconnect_serial_port()
                    if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                        for m in range(self.dual+1):
                            self.rfid.access_mode[self.port_no[m]-1] = 0
                    for m in range(self.dual+1):
                        self.mode[m] = 0 # Why you need to set 0 ?
                        self.send_event2(server=True, stream=6, function=11, code=0, subcode=2, msg_text="disable COM port", cs=m)
                        # if self.port_no2 > 0:
                        #     self.mode2 = 0 # Why you need to set 0 ?
                        #     self.send_event2(server=True, stream=6, function=11, code=0, subcode=2, msg_text="disable COM port", dual=self.port_no2)
        
                if not self.enable:
                    time.sleep(3)
                    continue

                if self.e84 == None:
                    self.connect_serial_port()
                    if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                        for m in range(self.dual+1):
                            self.rfid.access_mode[self.port_no[m]-1] = 2
                    for m in range(self.dual+1):
                        self.mode[m] = 2 # Why you need to set 2 ?
                        self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port", cs=m)
                    # self.mode = 2 # Why you need to set 2 ?
                    # self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port")
                    # if self.port_no2 > 0:
                    #     self.mode2 = 2 # Why you need to set 2 ?
                    #     self.send_event2(server=True, stream=6, function=11, code=0, subcode=1, msg_text="enable COM port", dual=self.port_no2)
                    if self.e84 != None:
                        # self.e84_cmd(link_reset)
                        # self.e84_cmd(enable0070)
                        # self.e84_cmd(reset)
                        # self.e84_cmd(auto)
                        # if self.dual:
                        #     self.e84_cmd(reset2)
                        #     self.e84_cmd(auto2)
                        pass
                    self.lastTime = time.time()
                    time.sleep(3)
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

                # if len(self.e84_queue) < 1:
                #     schedule.run_pending()

                # e84 write
                # if len(self.e84_queue) > 0:
                #     if self.e84 == None:
                #         continue
                #     else:
                #         self.e84.write(self.e84_queue.popleft())

                # res = self.e84.read(8) # <class 'bytes'>
                # res = self.e84.read(timeout=0.5)
                res = self.read(timeout=0.5)

                if res is None or res == '':
                    continue

                # print('tmp', res)
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
                    # self.e84_cmd(reset)
                    # self.e84_cmd(auto)
                    # if self.dual:
                    #     self.e84_cmd(reset2)
                    #     self.e84_cmd(auto2)
                    pass
                    # self.e84_cmd(mode_state)

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
                # elif status == '05':
                #     self.logger.info(f"{self.port_id[0]} E84 : This alarm have to be manual reset by operator {cmd}:{data} {status}")

                msg = ''
                
                if cmd == '0070':
                    if data == '0000':
                        # self.state['go'] = True
                        msg = 'GO ON'
                    elif data == '0001':
                        # self.state['go'] = False
                        msg = 'GO OFF'
                    elif data == '0002':
                        # self.state['valid'] = True
                        msg = 'VALID ON'
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
                    elif data == '0014':
                        # self.state['u_req'] = True
                        msg = 'U_REQ ON'
                    elif data == '0015':
                        # self.state['u_req'] = False
                        msg = 'U_REQ OFF'
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
                    elif data == '0026':
                        # self.state['select'] = True
                        msg = 'POWER ON'
                    elif data == '0027':
                        # self.state['select'] = False
                        msg = 'POWER OFF'
                    else:
                        msg = 'Unknown'

                    for m in range(self.dual+1):
                        self.send_event(False, int(cmd, 16), int(data, 16), msg, cs=m)
                    msg = cmd + ':' + data + ' ' + msg

                elif cmd == '0071':
                    # port_status = self.port_status
                    # port_status2 = self.port_status2
                    port_status = [-1]*settings.CS_NUMBER
                    for n in range(settings.CS_NUMBER):
                        port_status[n] = self.port_status[n]

                    if data in ['0001', '0002', '0003', '1002', '1003', '0004']:
                        msg = self.event_msg(data)
                        port_status[0] = int(data, 16)
                        self.port_status_msg[0] = msg
                        
                    # elif data == '0001':
                    #     msg = 'Ready to Load'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Ready to Load'
                    #     if self.rfid:
                    #         print(f"{self.port_id[0]} {cmd}:{data} Carrier_ID : {self.rfid_data}")
                    # elif data == '0002':
                    #     msg = 'Ready to Unload'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Ready to Unload'
                    #     if self.rfid:
                    #         print(f"{self.port_id[0]} {cmd}:{data} Carrier_ID : {self.rfid_data}")
                    # elif data == '0003':
                    #     msg = 'Load PS/PL Start'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Loading'
                    # elif data == '0004':
                    #     msg = 'Unload PS/PL Start'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Unloading'
                    # elif data == '0005':
                    #     msg = 'Load Complete'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Load Complete'
                    #     if self.rfid:
                    #         print(f"{self.port_id[0]} {cmd}:{data} Carrier_ID : {self.rfid_data}")
                    # elif data == '0006':
                    #     msg = 'Unload Complete'
                    #     port_status = int(data, 16)
                    #     self.port_status_msg = 'Unload Complete'
                    #     if self.rfid:
                    #         print(f"{self.port_id[0]} {cmd}:{data} Carrier_ID : {self.rfid_data}")
                    # elif data == '0007':
                    #     self.errorCode = 0
                    #     self.errorMsg = ''
                    #     msg = 'Auto Recover'
                    else:
                        if int(data[1:],16) in event71:
                            # if data[0] == '0':
                            #     msg = self.event_msg(data)
                            # else:
                            #     msg = self.event_msg(data, int(data[0],16)-1)
                            msg = self.event_msg(data)

                            # SmartIO-AGV comment out
                            # if data == '10fc':
                            #     self.alarm_id[0] = 0
                            #     self.alarm_text[0] = ''
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'CS0 Alarm OFF', 0)
                            # elif data == '20fc':
                            #     self.alarm_id[1] = 0
                            #     self.alarm_text[1] = ''
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'CS1 Alarm OFF', 1)
                            # elif data == '30fc':
                            #     self.alarm_id[2] = 0
                            #     self.alarm_text[2] = ''
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'CS2 Alarm OFF', 2)
                            # elif data == '00e1': # OC 13 IN ON Press Reset Button
                            #     self.alarm_id[0] = 0
                            #     self.alarm_text[0] = ''
                            #     self.alarm_id[1] = 0
                            #     self.alarm_text[1] = ''
                            #     self.alarm_id[2] = 0
                            #     self.alarm_text[2] = ''
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'Reset button', 0)
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'Reset button', 1)
                            #     self.send_event(True, int(cmd, 16), int(data, 16), 'Reset button', 2)

                            # elif data == '1101': # Idle
                            #     port_status[0] = 34
                            #     self.port_status_msg[0] = 'Idle'
                            # elif data == '1401': # Ready to Unload
                            #     port_status[0] = 2
                            #     self.port_status_msg[0] = 'Ready to Unload'
                            # elif data == '1501': # Unloading
                            #     port_status[0] = 4
                            #     self.port_status_msg[0] = 'Unloading'
                            # elif data == '1601': # Unload Completed
                            #     port_status[0] = 6
                            #     self.port_status_msg[0] = 'Unload Completed'
                            # elif data == '1801': # Ready to Load
                            #     port_status[0] = 1
                            #     self.port_status_msg[0] = 'Ready to Load'
                            # elif data == '1901': # Loading
                            #     port_status[0] = 3
                            #     self.port_status_msg[0] = 'Loading'
                            # elif data == '1a01': # Load Completed
                            #     port_status[0] = 5
                            #     self.port_status_msg[0] = 'Load Completed'
                            # elif data == '2101': # Idle(CS1)
                            #     port_status[1] = 35
                            #     self.port_status_msg[1] = 'Idle (CS1)'
                            # elif data == '2401': # Ready to Unload (CS1)
                            #     port_status[1] = 21
                            #     self.port_status_msg[1] = 'Ready to Unload (CS1)'
                            # elif data == '2501': # Unloading (CS1)
                            #     port_status[1] = 23
                            #     self.port_status_msg[1] = 'Unloading (CS1)'
                            # elif data == '2601': # Unload Completed (CS1)
                            #     port_status[1] = 25
                            #     self.port_status_msg[1] = 'Unload Completed (CS1)'
                            # elif data == '2801': # Ready to Load (CS1)
                            #     port_status[1] = 20
                            #     self.port_status_msg[1] = 'Ready to Load (CS1)'
                            # elif data == '2901': # Loading (CS1)
                            #     port_status[1] = 22
                            #     self.port_status_msg[1] = 'Loading (CS1)'
                            # elif data == '2a01': # Load Completed (CS1)
                            #     port_status[1] = 24
                            #     self.port_status_msg[1] = 'Load Completed (CS1)'
                            # elif data == '3101': # Idle(CS2)
                            #     port_status[2] = 36
                            #     self.port_status_msg[2] = 'Idle (CS2)'
                            # elif data == '3401': # Ready to Unload (CS2)
                            #     port_status[2] = 40
                            #     self.port_status_msg[2] = 'Ready to Unload (CS2)'
                            # elif data == '3501': # Unloading (CS2)
                            #     port_status[2] = 42
                            #     self.port_status_msg[2] = 'Unloading (CS2)'
                            # elif data == '3601': # Unload Completed (CS2)
                            #     port_status[2] = 44
                            #     self.port_status_msg[2] = 'Unload Completed (CS2)'
                            # elif data == '3801': # Ready to Load (CS2)
                            #     port_status[2] = 39
                            #     self.port_status_msg[2] = 'Ready to Load (CS2)'
                            # elif data == '3901': # Loading (CS2)
                            #     port_status[2] = 41
                            #     self.port_status_msg[2] = 'Loading (CS2)'
                            # elif data == '3a01': # Load Completed (CS2)
                            #     port_status[2] = 43
                            #     self.port_status_msg[2] = 'Load Completed (CS2)'
                        else:
                            msg = 'Unknown'

                    if data[0] == '0':
                        for m in range(self.dual+1):
                            self.load[m] = int(data, 16) # 0071 status
                    else:
                        # print(f"data[0] = {int(data[0])}")
                        m = int(data[0], 16) - 1
                        if m <= 7: # only support CS1, CS2
                            self.load[m] = int(data, 16)
                    
                    bSend = False
                    for m in range(self.dual+1):
                        # print(f"m={m}")
                        if self.port_status[m] != port_status[m] :
                            self.port_status[m] = port_status[m]
                            self.send_event(True, int(cmd, 16), int(data, 16), self.port_status_msg[m], cs=m)
                            bSend = True
                        
                    if not bSend:
                        for m in range(self.dual+1):
                            self.send_event(server=False, code=int(cmd, 16), subcode=int(data, 16), msg_text=msg, cs=m)
                    
                    msg = cmd + ':' + data + ' ' + msg

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
                        
                    except Exception as err:
                        self.logger.error(str(err))
                        
                    continue

                elif cmd == '0030':
                    self.logger.info(f"{self.port_id[m]} : cmd={cmd}, data={data}")

                elif cmd[0] == 0 or cmd[0] == '8':
                    msg = self.cmd_msg(cmd[1:])
                    msg = cmd + ':' + data + ' ' + msg
                    # if cmd == '8002' or cmd == '0002':
                    #     self.send_event(True, int(cmd, 16), int(data, 16), 'Alarm Reset')
                    #     msg = cmd + ':' + data + ' Alarm Reset'
                    # elif cmd == '8003':
                    #     msg = cmd + ':' + data + ' Write Auto/Manual mode'
                    #     num = int(data, 16)
                    #     self.mode_bit = num
                    #     for m in range(self.dual):
                    #         bit_value = (num >> (self.port_no[m] - 1)) & 1  # Extract bit at position 0
                    #         print(f"Bit {self.port_no[m]}: {bit_value}")

                    #         if bit_value:
                    #             if 1 != self.mode[m]:
                    #                 if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    #                     self.rfid.access_mode[self.port_no[m]-1] = 1 # Auto mode
                    #                 self.mode[m] = 1
                    #                 self.send_event(True, int(cmd, 16), 1, f"Change CS{m} to Auto", cs=m)
                    #                 msg = cmd + ':' + data + f" Change CS{m} to Auto"
                    #         else:
                    #             if 2 != self.mode[m]:
                    #                 if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    #                     self.rfid.access_mode[self.port_no[m]-1] = 2 # Manual mode
                    #                 self.mode[m] = 2
                    #                 self.send_event(True, int(cmd, 16), 2, f"Change CS{m} to Manual", cs=m)
                    #                 msg = cmd + ':' + data + f" Change CS{m} to Manual"

                    # elif cmd == '0003':
                    #     msg = cmd + ':' + data + ' Read Auto/Manual mode'
                    #     num = int(data, 16)
                    #     self.mode_bit = num

                    #     for m in range(self.dual):
                    #         bit_value = (num >> (self.port_no[m] - 1)) & 1  # Extract bit at position 1
                    #         print(f"Bit {self.port_no[m]}: {bit_value}")

                    #         if bit_value:
                    #             if 1 != self.mode[m]:
                    #                 if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    #                     self.rfid.access_mode[self.port_no[m]-1] = 1 # Auto mode
                    #                 self.mode[m] = 1
                    #                 self.send_event(True, int(cmd, 16), 1, f"CS{m} Auto", cs=m)
                    #                 msg = cmd + ':' + data + f" CS{m} Auto"
                    #         else:
                    #             if 2 != self.mode[m]:
                    #                 if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    #                     self.rfid.access_mode[self.port_no[m]-1] = 2 # Manual mode
                    #                 self.mode[m] = 2
                    #                 self.send_event(True, int(cmd, 16), 2, f"CS{m} Manual", cs=m)
                    #                 msg = cmd + ':' + data + f" CS{m} Manual"


                    # elif cmd == '001c':
                    #     msg = cmd + ':' + data + ' IO Action for Relay Output'

                    # elif cmd == '0010':
                    #     data2 = int(data[2:4], 16)
                    #     self.led['l_req'] = 1 if data2&0x01 else 0
                    #     self.led['u_req'] = 1 if data2&0x02 else 0
                    #     self.led['va'] = 1 if data2&0x04 else 0
                    #     self.led['ready'] = 1 if data2&0x08 else 0
                    #     self.led['vs_0'] = 1 if data2&0x10 else 0
                    #     self.led['vs_1'] = 1 if data2&0x20 else 0
                    #     self.led['ho_avbl'] = 1 if data2&0x40 else 0
                    #     self.led['es'] = 1 if data2&0x80 else 0
                    #     if self.e84_out != data2:
                    #         self.e84_out = data2
                    #         msg = cmd + ':' + data[2:4] + f"   OUT : ES: {self.led['es']}  HO_AVBL: {self.led['ho_avbl']}  VS_1: {self.led['vs_1']}  VS_0: {self.led['vs_0']}  READY: {self.led['ready']}  VA: {self.led['va']}  U_REQ: {self.led['u_req']}  L_REQ: {self.led['l_req']} "
                    #         # self.logger.info(f"{self.port_id} {msg}")
                    #         self.send_event(True, int(cmd, 16), data2, msg)
                    #         # self.mqtt_publish(int(cmd, 16), data2, 'E84 output')
                    #     # print('0010:', data[2:4], 'OUT : ES, HO_AVBL, VS_1, VS_0, READY, VA, U_REQ, L_REQ')
                    #     # continue
                    #     # msg = cmd + ':' + data[2:4] + f"   OUT : ES: {self.led['es']}  HO_AVBL: {self.led['ho_avbl']}  VS_1: {self.led['vs_1']}  VS_0: {self.led['vs_0']}  READY: {self.led['ready']}  VA: {self.led['va']}  U_REQ: {self.led['u_req']}  L_REQ: {self.led['l_req']} "
                    #     continue
                    # elif cmd == '0011':
                    #     data2 = int(data[2:4], 16)
                    #     self.led['valid'] = 1 if data2&0x01 else 0
                    #     self.led['cs_0'] = 1 if data2&0x02 else 0
                    #     self.led['cs_1'] = 1 if data2&0x04 else 0
                    #     self.led['am_avbl'] = 1 if data2&0x08 else 0
                    #     self.led['tr_req'] = 1 if data2&0x10 else 0
                    #     self.led['busy'] = 1 if data2&0x20 else 0
                    #     self.led['compt'] = 1 if data2&0x40 else 0
                    #     self.led['cont'] = 1 if data2&0x80 else 0
                    #     if self.e84_in != data2:
                    #         self.e84_in = data2
                    #         msg = cmd + ':' + data[2:4] + f"   IN : CONT: {self.led['cont']}  COMPT: {self.led['compt']}  BUSY: {self.led['busy']}  TR_REQ: {self.led['tr_req']}  AM_AVBL: {self.led['am_avbl']}  CS_1: {self.led['cs_1']}  CS_0: {self.led['cs_0']}  VALID: {self.led['valid']} "
                    #         # self.logger.info(f"{self.port_id} {msg}")
                    #         self.send_event(True, int(cmd, 16), data2, msg)
                    #         # self.mqtt_publish(int(cmd, 16), data2, 'E84 input')
                    #     # print('0011:', data[2:4], 'IN : CONT, COMPT, BUSY, TR_REQ, AM_AVBL, CS_1, CS_0, VALID')
                    #     # continue
                    #     # msg = cmd + ':' + data[2:4] + f"   IN : CONT: {self.led['cont']}  COMPT: {self.led['compt']}  BUSY: {self.led['busy']}  TR_REQ: {self.led['tr_req']}  AM_AVBL: {self.led['am_avbl']}  CS_1: {self.led['cs_1']}  CS_0: {self.led['cs_0']}  VALID: {self.led['valid']} "
                    #     continue
                    # elif cmd == '0012':
                    #     data2 = int(data[2:4], 16)
                    #     self.gpio1['go'] = 1 if data2&0x01 else 0
                    #     self.gpio1['mode'] = 1 if data2&0x02 else 0
                    #     self.gpio1['select'] = 1 if data2&0x04 else 0
                    #     if self.e84_smg != data2:
                    #         self.e84_smg = data2
                    #         msg = cmd + ':' + data[2:4] + f"   SELECT: {self.gpio1['select']}  MODE: {self.gpio1['mode']}  GO: {self.gpio1['go']} "
                    #         # self.logger.info(f"{self.port_id} {msg}")
                    #         self.send_event(True, int(cmd, 16), data2, msg)
                    #         # self.mqtt_publish(int(cmd, 16), data2, 'SELECT, MODE, GO')
                    #     # print('0012:', data[2:4], 'SELECT, MODE, GO')
                    #     # continue
                    #     # msg = cmd + ':' + data[2:4] + f"   SELECT: {self.gpio1['select']}  MODE: {self.gpio1['mode']}  GO: {self.gpio1['go']} "
                    #     continue
                else:
                    for m in range(self.dual+1):
                        self.send_event(server=True, code=int(cmd, 16), subcode=int(data,16), msg_text='Unknown cmd', cs=m)
                    msg = cmd + ':' + data + ' ' + status + " Unknown cmd"

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
                    self.logger.info(f"{self.port_id[0]} {msg}")

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
                # self.e84.stop()
                self._run_coro(self.alarm_reset_async())
                #logger.error(traceback.format_exc())
                time.sleep(3)

if __name__ == "__main__":
    # e84 = E84('/dev/ttyUSB0')
    e84 = SmartE84('COM3')
    e84.daemon = True
    e84.start()

    #tmp_cmd = (0x55, 0xAA, 0x80, 0x59, 0x00, 0x00)
    #e84.e84_cmd(tmp_cmd)

    stop = False
    time.sleep(1)

    while not stop:
        #tmp = raw_input('input:')
        tmp = input('input:')
        tmp = str(tmp)
        if tmp == '1':
            e84.e84_cmd(manual)
        elif tmp == '2':
            e84.e84_cmd(auto)
        elif tmp == '3':
            e84.e84_cmd(ps_on)
        elif tmp == '4':
            e84.e84_cmd(ps_off)
        elif tmp == '5':
            e84.e84_cmd(reset)
        elif tmp == '01':
            e84.e84_cmd(e84_out)
            print(e84.led)
        elif tmp == '02':
            e84.e84_cmd(e84_in)
            print(e84.led)
        elif tmp == '03':
            e84.e84_cmd(pspl)
            #print(e84.led)
        elif tmp == '0':
            # print(e84.state)
            e84.e84_cmd(version)
            # e84.e84_cmd(version2)
            cd = bytes.fromhex('55AA00010000')
            e84.e84_cmd(cd)
        elif tmp == '8':
            e84.e84_cmd((0x55, 0xAA, 0x80, 0x16, 0x00, 0x03))
        elif tmp == '9':
            e84.e84_cmd((0x55, 0xAA, 0x80, 0x16, 0x00, 0x01))
        elif tmp == 'v':
            e84.e84_cmd((0x55, 0xAA, 0x00, 0x00, 0x01, 0x00))
        time.sleep(0.5)
	
