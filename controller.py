from threading import Thread
from time import sleep, time
from datetime import datetime

import collections
from collections import OrderedDict
import re
import traceback
from config import Settings, settings
import json

from mqtt_svc import MQTTSvc
from event import EventMgr
if settings.E84_TYPE == 2:
    from smart_e84 import SmartE84
else:
    from e84 import E84
from rfid import Sunion, SunionPS
from rfid_UHF_RegalScan import SunionUHF_RS
from rfid_UHF_SILION import SunionUHF_SL
# from ui_form import UIForm
import logging
from logging.handlers import TimedRotatingFileHandler
import os

if settings.FTP_ENABLE:
    from ftp_svc import FTPSvc
if settings.WEB_SERVICE_ENABLE:
    from webservice_svc import WebServiceSvc
if settings.API_ENABLE:
    from api_svc import APISvc
if settings.LED_ENABLE:
    from sync_led_controller import SyncLEDController

class Controller(Thread):
    def __init__(self, logger, sio = None) -> None:
        Thread.__init__(self)
        self.stop = False
        self.tsc_logger = logger
        # self.sender = sender
        self.sio = sio
        self.receive_queue = collections.deque()
        self.alarms = {}
        self.loadport = {}
        self.device_id = settings.DEVICE_ID
        self.rfid = None
        self.rfid_UHF = None
        self.log_preserve = 30
        self.event_mgr = None
        self.ftp_svc = None
        self.webservice_svc = None
        self.led_controller = None
        self.api_svc = None
        self.equipment_state = -1 # 0:Down, 1:Alarm, 2:Idle, 3:Execute, 4:Manual, 5:Pause
        
    def data_process(self, data):
        print(data)

    def mqtt_publish_status(self, type=3, code=0, subcode=0, msg_text='eqp status'):
        # if not settings.MQTT_RFID_MSG_ENABLE:
        #     return
        
        data = OrderedDict()
        
        # data['Server'] = True

        config = OrderedDict()
        config['load_port_number'] = settings.LOAD_PORT_NUMBER

        if settings.FTP_ENABLE:
            config['ftp'] = True
        else:
            config['ftp'] = False
        if settings.LF_RFID_ENABLE:
            config['rfid_LF'] = True
        else:
            config['rfid_LF'] = False
        if settings.UHF_RFID_ENABLE:
            config['rfid_UHF'] = True
        else:
            config['rfid_UHF'] = False
        if settings.WAFER_TYPE: # 0:All, 1:Only Port1, 2:Only Port2
            config['wafer'] = settings.WAFER_TYPE
        else:
            config['wafer'] = settings.WAFER_TYPE

        data['device_id'] = settings.DEVICE_ID
        data['eqp_state'] = self.equipment_state
        data['config'] = config
        data['type'] = type
        data['stream'] = -1
        data['function'] = -1
        data['code_id'] = code
        data['sub_id'] = subcode
        data['msg_text'] = msg_text
        data['status'] = ''
        data['occurred_at'] = time()
        # print(json.dumps(data))
        self.event_mgr.on_notify(data)
        
    def stop_e84(self):
        for i in range(0,len(self.e84)):
            self.e84[i].stop = True
        
    def run(self):
        # config = Settings()

        while not self.stop:
            try:
                if settings.LED_ENABLE:
                    try:
                        self.led_controller = SyncLEDController(port=f"COM{settings.LED_COM}", address=settings.LED_Address, response_timeout=2.0, logger=self.tsc_logger)
                        self.tsc_logger.info("LED device connecting")
                        if self.led_controller.connect():
                            self.tsc_logger.info("LED device connection successful")
                            if self.led_controller.set_address(settings.LED_Address):
                                if not self.led_controller.turn_off_all():
                                    self.tsc_logger.info("Turn off all LEDs failed")
                            else:
                                self.tsc_logger.info("Set LED device address failed")
                            
                        else:
                            self.tsc_logger.info("LED device connection failed")
                        
                    except Exception as e:
                        self.tsc_logger.info(f"Error: {e}")
                        import traceback
                        traceback.print_exc()
                if settings.FTP_ENABLE: 
                    self.ftp_svc = FTPSvc(self, self.tsc_logger)
                if settings.WEB_SERVICE_ENABLE:
                    self.webservice_svc = WebServiceSvc(self, self.tsc_logger)
                if settings.API_ENABLE:
                    self.api_svc = APISvc(self, self.tsc_logger)
                self.mqtt_svc = MQTTSvc(self, self.tsc_logger)
                self.event_mgr = EventMgr(self, self.tsc_logger)
                if self.ftp_svc:
                    self.event_mgr.add_svc(self.ftp_svc)
                if self.webservice_svc:
                    self.event_mgr.add_svc(self.webservice_svc)
                self.event_mgr.add_svc(self.mqtt_svc)
                self.tsc_logger.info('Controller Starting')
                # print('AEI: ', config.aei_ip, config.aei_port)
                # self.e82.enable()
                if settings.LF_RFID_ENABLE :
                    # self.rfid = Sunion(devPath='COM'+str(settings.LF_RFID_COM), type='LF', event_mgr=self.event_mgr, portNumber=settings.LOAD_PORT_NUMBER)
                    if settings.RFID_READ_PS_ENABLE or settings.RFID_DEVICE_ONLY :
                        self.rfid = SunionPS(devPath='COM'+str(settings.LF_RFID_COM), name='1', type='LF', controller=self, event_mgr=self.event_mgr, portNumber=settings.LOAD_PORT_NUMBER, trycount=settings.LF_RFID_TRY_COUNT, pickcount=settings.LF_RFID_PICK_COUNT)
                        self.rfid.daemon = True
                        self.rfid.start()
                    else:
                        self.rfid = Sunion(devPath='COM'+str(settings.LF_RFID_COM), name='1', type='LF', controller=self, event_mgr=self.event_mgr, portNumber=settings.LOAD_PORT_NUMBER, trycount=settings.LF_RFID_TRY_COUNT, pickcount=settings.LF_RFID_PICK_COUNT)
                if settings.UHF_RFID_ENABLE :
                    if settings.UHF_RFID_TYPE == 0:
                        self.rfid_UHF = SunionUHF_RS(devPath='COM'+str(settings.UHF_RFID_COM), type='UHF_RS', controller=self, event_mgr=self.event_mgr, trycount=settings.UHF_RFID_TRY_COUNT, pickcount=settings.UHF_RFID_PICK_COUNT, timeout=settings.UHF_RFID_TIMEOUT)
                    else:
                        self.rfid_UHF = SunionUHF_SL(devPath='COM'+str(settings.UHF_RFID_COM), type='UHF_SL', controller=self, event_mgr=self.event_mgr, trycount=settings.UHF_RFID_TRY_COUNT, pickcount=settings.UHF_RFID_PICK_COUNT, timeout=settings.UHF_RFID_TIMEOUT)
                    self.rfid_UHF.daemon = True
                    self.rfid_UHF.start()
                self.e84 = {}
                for i in range(0,settings.LOAD_PORT_NUMBER):
                    enable = getattr(settings, f"LOAD_PORT_{i+1}_ENABLE", False)
                    # if enable :
                    # do not process dual port first
                    dual = getattr(settings, f"LOAD_PORT_{i+1}_DUAL", False)
                    if dual:
                        continue
                    
                    com = getattr(settings, f"LOAD_PORT_{i+1}_COM", False)
                    if com :
                        port_id = getattr(settings, f"LOAD_PORT_{i+1}_ID", False)
                        led_id = getattr(settings, f"LOAD_PORT_{i+1}_LED_ID", False)
                        if settings.E84_TYPE == 2:
                            self.e84[i] = SmartE84(f'COM{com}', controller=self, log=self.tsc_logger, enable=enable, port_no=i+1, port_id=port_id, rfid=self.rfid, event_mgr=self.event_mgr)
                        else:
                            # self.e84[i] = E84(f'COM{com}', controller=self, log=self.tsc_logger, enable=enable, port_no=i+1, port_id=f'LP{i+1}', rfid=self.rfid, event_mgr=self.event_mgr, ui=self)
                            if settings.DUAL_RFID:
                                self.e84[i] = E84(f'COM{com}', controller=self, log=self.tsc_logger, enable=enable, port_no=i+1, port_id=port_id, rfid=self.rfid, rfid2=self.rfid_UHF, event_mgr=self.event_mgr, led_id=led_id)
                            else:
                                if settings.UHF_RFID_ENABLE:
                                    self.e84[i] = E84(f'COM{com}', controller=self, log=self.tsc_logger, enable=enable, port_no=i+1, port_id=port_id, rfid=self.rfid_UHF, event_mgr=self.event_mgr, led_id=led_id)
                                else:
                                    self.e84[i] = E84(f'COM{com}', controller=self, log=self.tsc_logger, enable=enable, port_no=i+1, port_id=port_id, rfid=self.rfid, event_mgr=self.event_mgr, led_id=led_id)
                        self.e84[i].daemon = True
                        self.e84[i].start()
                        self.loadport[i+1] = {}
                        self.loadport[i+1]['enable'] = enable
                        self.loadport[i+1]['com'] = 'e84'
                        self.loadport[i+1]['ver'] = settings.E84_TYPE
                        self.loadport[i+1]['id'] = i
                        self.loadport[i+1]['dual'] = 0
                        print(f"E84 loadport : {self.e84[i].port_no[0]}, {self.e84[i].port_no[1]}, {self.e84[i].port_no[2]}, {self.e84[i].dual}")

                    else:
                        self.loadport[i+1] = {}
                        self.loadport[i+1]['enable'] = enable
                        self.loadport[i+1]['com'] = 'rfid'
                        self.loadport[i+1]['ver'] = 0
                        self.loadport[i+1]['id'] = i
                        print(f"RFID loadport : {i+1}")

                    type = getattr(settings, f"LOAD_PORT_{i+1}_RFID", False)
                    if type :
                        self.loadport[i+1]['type'] = type
                    else:
                        self.loadport[i+1]['type'] = None
                    print(f"LP_{i+1} start, {self.loadport[i+1]['type']}")

                for i in range(0,settings.LOAD_PORT_NUMBER):
                    enable = getattr(settings, f"LOAD_PORT_{i+1}_ENABLE", False)
                    # if enable :
                    # skip normal port which already process 
                    dual = getattr(settings, f"LOAD_PORT_{i+1}_DUAL", False)
                    if not dual:
                        continue
                    
                    com = getattr(settings, f"LOAD_PORT_{i+1}_COM", False)
                    
                    if com :
                        port_id = getattr(settings, f"LOAD_PORT_{i+1}_ID", False)
                        for id, e84 in self.e84.items():
                            if e84.devPath == f'COM{com}':
                                e84.dual = i
                                e84.port_no[i] = i+1
                                e84.port_id[i] = port_id
                                
                                self.loadport[i+1] = {}
                                self.loadport[i+1]['enable'] = enable
                                self.loadport[i+1]['com'] = 'e84'
                                self.loadport[i+1]['ver'] = settings.E84_TYPE
                                self.loadport[i+1]['id'] = id
                                self.loadport[i+1]['dual'] = i

                                print(f"E84 loadport dual : {e84.port_no[0]}, {e84.port_no[1]}, {e84.port_no[2]}, {e84.dual}")
                                break

                    type = getattr(settings, f"LOAD_PORT_{i+1}_RFID", False)
                    if type :
                        self.loadport[i+1]['type'] = type
                    else:
                        self.loadport[i+1]['type'] = None
                    print(f"LP_{i+1} start, {self.loadport[i+1]['type']}")

                # self.uiform = UIForm(self.e84)
                # self.uiform.daemon = True
                # self.uiform.start()
                
                timeout_counter = 0
                start_up = True
                while not self.stop:
                    try:
                        while self.receive_queue:
                            data = self.receive_queue.popleft()
                            self.data_process(data)

                        sleep(0.01)
                    except KeyboardInterrupt:
                        self.tsc_logger.warning('IPC killed by user')
                        self.stop = True
                    except:
                        self.tsc_logger.error(traceback.format_exc())
                        pass
                else:
                    self.tsc_logger.warning('IPC Stopping')
                    if settings.LED_ENABLE:
                        try:
                            self.tsc_logger.info("\n--- LED device disconnecting ---")
                            self.led_controller.disconnect()
                            self.tsc_logger.info("\n--- LED device disconnected ---")
                        except Exception as e:
                            self.tsc_logger.info(f"Error: {e}")
                            import traceback
                            traceback.print_exc()
                    if self.rfid:
                        self.rfid.stop = True
                    if self.rfid_UHF:
                        self.rfid_UHF.stop = True
                    self.stop_e84()
                    if self.ftp_svc:
                        self.ftp_svc.stop = True
                    if self.mqtt_svc:
                        self.mqtt_svc.stop = True
                    if self.event_mgr:
                        self.event_mgr.stop = True
                    self.tsc_logger.warning('IPC Stopped')
            except:
                self.tsc_logger.error(traceback.format_exc())
                if settings.LED_ENABLE:
                    try:
                        self.tsc_logger.info("\n--- LED device disconnecting ---")
                        self.led_controller.disconnect()
                        self.tsc_logger.info("\n--- LED device disconnected ---")
                    except Exception as e:
                        self.tsc_logger.info(f"Error: {e}")
                        import traceback
                        traceback.print_exc()
                if self.rfid:
                    self.rfid.stop = True
                if self.rfid_UHF:
                    self.rfid_UHF.stop = True
                self.stop_e84()
                if self.ftp_svc:
                    self.ftp_svc.stop = True
                if self.mqtt_svc:
                    self.mqtt_svc.stop = True
                if self.event_mgr:
                    self.event_mgr.stop = True
                self.stop = True
                
                
                