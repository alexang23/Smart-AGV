from threading import Thread
from time import sleep
# from datetime import datetime

import collections
# import re
import traceback
# from models.server import Server
# from database import get_db
import sys
#from global_variables import alarm_queue, logger
#from global_variables import logger
import schedule

# import requests
# import json
# from fastapi.encoders import jsonable_encoder
from config import settings
from datetime import datetime

# import paho.mqtt.client as mqtt
# from paho.mqtt.packettypes import PacketTypes
# from models.message import Message

#### test OK version

# ## MQTT v5 add 1 parameter compare to MQTT v3xx
# def on_connect(thread, mqttc, obj, flags, rc):
#     print("########## connect rc: " + str(rc))
    
# def on_connect_fail(mqttc, userdata):
#     print("########## on_connect_fail: " + str(userdata))

# def on_message(mqttc, obj, msg):
#     print("########## " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

# def on_publish(mqttc, obj, mid):
#     print("########## mid: " + str(mid))

# ## MQTT v5 add 1 parameter compare to MQTT v3xx
# def on_subscribe(thread, mqttc, obj, mid, granted_qos):
#     print("########## Subscribed: " + str(mid) + " " + str(granted_qos))

# def on_log(mqttc, obj, level, string):
#     print("########## on_log : " + string)


# class EventMgr(Thread):
class EventMgr:
    __instance=None

    @staticmethod
    def getInstance():

        if EventMgr.__instance==None:
            EventMgr()

        return EventMgr.__instance
    
    def __init__(self, controller, logger) -> None:
        EventMgr.__instance=self

        self.stop = False
        self.controller = controller
        # self.uiform = uiform ## no used
        self.logger = logger
        self.receive_queue = collections.deque()
        self.svclist = []
        self.svr_enable = True
        # self.alarms = {}
        # self.ip = settings.MQTT_IP
        # self.port = settings.MQTT_PORT
        # self.device_id = settings.DEVICE_ID
        # self.client_id = settings.MQTT_CLIENT_ID
        # self.topic = settings.MQTT_TOPIC
        # self.topic_server = settings.MQTT_TOPIC_SERVER
        # self.mqttc = None

        # Thread.__init__(self)
        # self.setDaemon(True)
        # self.start()

    def add_svc(self, svc):
        self.svclist.append(svc)

    def on_notify(self, data):
        for svc in self.svclist:
            if svc.svc_name == 'ftp':
                if not hasattr(data, 'event'):
                    if svc.ftp_enable and data['type'] == 0 and (data['code_id'] == 128 or (data['code_id'] == 73 and data['sub_id'] != 0)): # 0x0080 128, 0x0049 73
                        # print(f"[{data['msg_text'][7:11]}]")
                        if (svc.alarm_mode == 5 and data['msg_text'][10] == '5') or svc.alarm_mode != 5:
                            data['event'] = 'Alarm'
                            data['class'] = 'E84'
                            svc.on_notify(data)
            else:
                svc.on_notify(data)
        # self.receive_queue.append(data)
        #logger.debug('{}'.format(data))

        
    # def enable_webapi(self, set):
    #     self.svr_enable = set
    #     self.logger.info('WebAPI Server enable = {}'.format(set))
        
    # def update_webapi(self, ip, port, url):
    #     if self.ip != ip :
    #         self.logger.info('WebAPI Server IP change from {} to {}.'.format(self.ip, ip))
    #         self.ip = ip
    #     if self.port != port :
    #         self.logger.info('WebAPI Server Port change from {} to {}.'.format(self.port, port))
    #         self.port = port
    #     if self.url != url :
    #         self.logger.info('WebAPI Server URL change from {} to {}.'.format(self.url, url))
    #         self.url = url


        
    # def superuser_login(self, data):
    #     message = {}
    #     message['userid'] = "gyro"
    #     message['password'] = "gsi5613686"

    #     response = {}
    #     response['result'] = 'NG'
    
    #     res = None
    #     # ipc_ip = data['params']['ip']
    #     # api_port = data['params']['api_port']
    #     try:
    #         res = requests.post('http://{}:{}/api/auth/login'.format(self.ip, self.port), json=message, timeout=5)
    #     except requests.ConnectionError:
    #         self.logger.error('webapi_svc.py superuser_login error : requests.ConnectionError')
    #         response['status_code'] = 503
    #         response['reason'] = 'requests.ConnectionError'
    #         return response
    #     except requests.Timeout:
    #         self.logger.error('webapi_svc.py superuser_login error : requests.Timeout')
    #         response['status_code'] = 408
    #         response['reason'] = 'requests.Timeout'
    #         return response
    #     except Exception as err:
    #         self.logger.error('webapi_svc.py superuser_login error : {}'.format(str(err)))
    #         response['status_code'] = 400
    #         response['reason'] = str(err)
    #         return response
        
    #     #print('requests.post : [{}] {}'.format(res.status_code, res.text))
    #     response['status_code'] = res.status_code
    #     response['reason'] = res.reason
    #     #print(response)
        
    #     if res.status_code == 200 :
    #         response['result'] = 'success'
    #         response['access_token'] = json.loads(res.text)['access_token']
    #         #print(access_token)

    #     return response

    def data_process(self, data):
        return
        try:
            
            # print(data)
            # self.mqtt.publish(settings.MQTT_TOPIC, data)
            
            tmp = datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
            # msg_txt = f"########## {tmp} : {str(data)}"
            # msg_txt = data
            # msg_txt = str(data) ## python dictionary format which using single quotes
            msg_txt = str(data).replace("'",'"') ## json format which using double quotes
            # print(f"########## Publishing: {tmp} {msg_txt}")

            if 'cmd' in data:
                props = mqtt.Properties(PacketTypes.PUBLISH)
                props.CorrelationData = data['correlation'].CorrelationData
                reply_to = data['correlation'].ResponseTopic
                del data['correlation']
                payload = json.dumps(data)
                print("Sending response "+str(data['result'])+" on '" + reply_to + "': "+str(props.CorrelationData))
                # infot = self.mqttc.publish(self.topic+'/Response', msg_txt, qos=settings.MQTT_QOS)
                # infot = self.mqttc.publish(self.topic+'/Response', msg_txt, qos=settings.MQTT_QOS)
                infot = self.mqttc.publish(reply_to, payload, qos=1, properties=props)
                infot.wait_for_publish(5)
                return

            if 'device_id' in data:
            # if  data['type'] == 0 and \
            #     (   data['code_id'] == 5 or \
            #         data['code_id'] == 113 or \
            #         data['code_id'] >= 128 ):
            
                # msg_txt = str(data).replace("'",'"')
                # infot = self.mqttc.publish(self.topic_server, msg_txt, qos=settings.MQTT_QOS)
                payload = json.dumps(data)
                infot = self.mqttc.publish(self.topic_server, payload, qos=settings.MQTT_QOS)
                # infot.wait_for_publish(5)
                del data['device_id']

            # infot = self.mqttc.publish(self.topic, msg_txt, qos=settings.MQTT_QOS)
            payload = json.dumps(data)
            infot = self.mqttc.publish(self.topic, payload, qos=settings.MQTT_QOS)
            # infot.wait_for_publish(5)
            

        except Exception as err:
            print('****************** ' + str(err))
    
        return
        if 'ALARM' in data['class'] or 'EVENT' in data['class']:
            res = None
            
            # response = self.superuser_login(data)
            
            # if response['result'] != 'success' :
            #     return
            
            # header = {}
            # header['Authorization'] = 'Bearer {}'.format(response['access_token'])
            
            #self.logger.debug('requests.post : {}'.format(data))
            try:
                # ipc_ip = data['params']['ip']
                # ipc_port = data['params']['port']
                # api_port = data['params']['api_port']
                # ipc_enable = data['params']['ipc_enable']
                # ftp_enable = data['params']['ftp_enable']
                payload = json.dumps(data)
                # print(payload)
                # url = 'http://{}:{}/api/test{}?payload={}'.format(self.ip, self.port, self.url, payload)
                url = 'http://{}:{}{}'.format(self.ip, self.port, self.url)
                # res = requests.post(url, headers=header, json=payload, timeout=5)
                # res = requests.post(url, headers=header, timeout=5)
                res = requests.post(url, json=payload, timeout=5)
                
            except requests.ConnectionError:
                self.logger.error('requests.ConnectionError : {}'.format(url))
                return
            except requests.Timeout:
                self.logger.error('requests.Timeout : {}'.format(url))
                return
            except:
                self.logger.error(traceback.format_exc())
                return
                
            #self.logger.debug('requests.post : [{}] {}'.format(res.status_code, res.text))
            response = json.loads(res.text)
            response['status_code'] = res.status_code
            response['reason'] = res.reason
            #print(response)
            
            if res.status_code != 200:
                pass
            else:
                pass

    def memory_check(self):
        if not self.svr_enable:
            return
        
        try:
            receive_queue_size = len(self.receive_queue)
            
            stdout_size = sys.getsizeof(sys.stdout)
                
            self.logger.info(f"event_svc : receive_queue = {receive_queue_size}, stdout = {stdout_size}")
            # self.logger.info(f"{self.port_id} : stdout = {stdout_size}, logger size = {sys.getsizeof(self.logger)}, logger file = {self.logger.getfilestreamsize()}, logger stream = {self.logger.getstdoutstreamsize()}, logger sql = {self.logger.getsqlstreamsize()}")
        except Exception as err:
            print(str(err))
            
    def run(self):
        self.logger.info('EventMgr Starting')
        # db = next(get_db())
        
        # if settings.MEMORY_CHECK:
        #     schedule.every(5).minutes.do(self.memory_check)
        
        while not self.stop :
            while self.receive_queue :
                data = self.receive_queue.popleft()
                # self.logger.debug('inside webapi_svr run = {}'.format(data))
                # print('inside mqtt_svr run = {}'.format(data))
                if self.svr_enable :
                    pass
                    # self.data_process(data)
                    # if 'device_id' in data:
                    #     del data['device_id']
                    # try:
                    #     msg = Message(port_id=data['port_id'],
                    #                   port_no=data['port_no'],
                    #                   dual_port=data['dual_port'],
                    #                   type=data['type'],
                    #                   stream=data['stream'],
                    #                   function=data['function'],
                    #                   code_id=data['code_id'],
                    #                   sub_id=data['sub_id'],
                    #                   msg_text=data['msg_text'],
                    #                   status=data['status'],
                    #                   occurred_at=datetime.fromtimestamp(data['occurred_at'], timezone.utc)
                    #                   )
                    #     db.add(msg)
                    #     db.commit()
                    # except Exception as err:
                    #     db.rollback()
                    #     print(str(err))
                        
            # if settings.MEMORY_CHECK:
            #     schedule.run_pending()
            sleep(0.1)
            # print('inside mqtt_svr')
            
            
