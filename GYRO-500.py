from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse
# from fastapi.responses import RedirectResponse
# from fastapi_mqtt import FastMQTT, MQTTConfig
from contextlib import asynccontextmanager
from config import settings
# from global_variables import app, mqtt
from global_log import Logger, LoggerFastAPI, glogger

from threading import Thread
from functools import lru_cache
# from logging.handlers import TimedRotatingFileHandler
# import re
# from typing import Optional
# import logging
# import traceback
# import json

import uvicorn
import time
import collections
import sys
import os

#from global_log import EndpointFilter
# from global_log import glogger
from routers import user, auth, info, update, port, eqp, log, test #, setting
# from mqtt_svc import MQTTSvc
from controller import Controller

# tsc = Controller(Logger('tsc', 'mcs.log'), Sender())
tsc = Controller(Logger('ipc', 'ipc.log'))
# tsc = Controller(glogger)

app_logger = Logger('App', 'app.log')

@asynccontextmanager
async def _lifespan(app: FastAPI):
    # # mqtt_config = MQTTConfig(host = "192.168.0.151",
    # mqtt_config = MQTTConfig(host = settings.MQTT_IP,
    #     port= settings.MQTT_PORT,
    #     keepalive = 60,
    #     username=settings.MQTT_USERNAME,
    #     password=settings.MQTT_PASSWORD)
    # mqtt = FastMQTT(
    #     config=mqtt_config
    # )

    # @mqtt.on_connect()
    # def connect(client, flags, rc, properties):
    #     # mqtt.client.subscribe("$SYS/#") #subscribing mqtt topic
    #     mqtt.client.subscribe(settings.MQTT_TOPIC) #subscribing mqtt topic
    #     print("########## Connected: ", client, flags, rc, properties)

    # @mqtt.on_message()
    # async def message(client, topic, payload, qos, properties):
    #     print("########## Received message: ",topic, payload.decode(), qos, properties)

    # # @mqtt.subscribe("my/mqtt/topic/#")
    # # async def message_to_topic(client, topic, payload, qos, properties):
    # #     print("########## Received message to specific topic: ", topic, payload.decode(), qos, properties)

    # # @mqtt.subscribe("my/mqtt/topic/#", qos=2)
    # @mqtt.subscribe(settings.MQTT_TOPIC, qos=2)
    # async def message_to_topic_with_high_qos(client, topic, payload, qos, properties):
    #     print("########## Received message to specific topic and QoS=2: ", topic, payload.decode(), qos, properties)
        
    # @mqtt.on_disconnect()
    # def disconnect(client, packet, exc=None):
    #     print("########## Disconnected")

    # @mqtt.on_subscribe()
    # def subscribe(client, mid, qos, properties):
    #     print("########## subscribed", client, mid, qos, properties)
        
    # global glogger
    # glogger = Logger('api', 'api.log')
    # glogger = LoggerFastAPI('api.log')
    # glogger.init()
                
    global glogger
    glogger = LoggerFastAPI('api.log').get_logger()
    app.state.glogger = glogger
        
    app.state.tsc = tsc
    app.state.receive_queue = collections.deque()
    # log_handler = Logger('webapi', 'webapi.log')
    # app.state.mqtt_svc = MQTTSvc(log_handler, mqtt)

    # await mqtt.mqtt_startup()
    # await mqtt.connection()
    
    tsc_thread = Thread(target=tsc.run, daemon=True)
    tsc_thread.start()
    
    # logging.info("connection done, starting fastapi app now")
    # print("########## connection done, starting fastapi app now")
    app.state.glogger.info("########## connection done, starting fastapi app now")
    yield
    # await mqtt.mqtt_shutdown()
    # await mqtt.client.disconnect()
    # print("########## disconnect done, shutdown fastapi app now")
    app.state.glogger.info("########## disconnect done, shutdown fastapi app now")

# def init_logging():
#     global glogger
#     glogger = LoggerFastAPI('api.log')

app = FastAPI(lifespan=_lifespan)
# app.add_event_handler("startup", init_logging)

origins = [
    settings.CLIENT_ORIGIN,
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#logging.getLogger('uvicorn.access').addFilter(EndpointFilter())

# @app.get("/")
# async def root():
#     # return FileResponse("static/main.html")
#     return RedirectResponse(url="/web/main.html")

app.include_router(auth.router, tags=['Auth'], prefix='/api/auth')
app.include_router(user.router, tags=['User'], prefix='/api/user')
# app.include_router(setting.router, tags=['Setting'], prefix='/api/setting')
app.include_router(port.router, tags=['Port'], prefix='/api/port')
app.include_router(eqp.router, tags=['Equipment'], prefix='/api/eqp')
app.include_router(update.router, tags=['Update'], prefix='/api/update')
# app.include_router(ipc.router, tags=['IPC'], prefix='/api/ipc')
# app.include_router(server.router, tags=['Server'], prefix='/api/server')
# app.include_router(ftp.router, tags=['FTP'], prefix='/api/ftp')
app.include_router(log.router, tags=['Log'], prefix='/api/log')
# app.include_router(event.router, tags=['Event'], prefix='/api/event')
# app.include_router(alarm.router, tags=['Alarm'], prefix='/api/alarm')
# app.include_router(message.router, tags=['Message'], prefix='/api/message')
app.include_router(info.router, tags=['Info'], prefix='/api/info')
app.include_router(test.router, tags=['Test'], prefix='/api/test')

# @app.get("testmqtt")
# # async def test_mqtt(request: Request, message: str):
# async def test_mqtt():
#     global mqtt
#     # mqtt.publish("/mqtt", "Hello from Fastapi") #publishing mqtt topic
#     mqtt.publish(settings.MQTT_TOPIC, "########## Hello from Fastapi")
#     # mqtt.publish(settings.MQTT_TOPIC, message)
#     return {"result": True, "message": "Published" }

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()

    # header = request.headers
    # print(f"Request Header: {str(header)}")
    
    # # Access the content of the request body
    # body = await request.body()
    # print(f"Request Body: {body.decode()}")

    response = await call_next(request)
    process_time = time.time() - start_time
    #print('process_time {} : {}'.format(request.url, process_time))
    response.headers["X-Process-Time"] = str(process_time)
    return response

# @lru_cache(maxsize=1)
# def get_config():
#     #config = Config()
#     config = settings
#     return config

# app.mount('/',StaticFiles(directory='web', html=True), name='web')

import ctypes

def disable_quick_edit_mode():
    """
    Disables Quick Edit Mode for the current console window on Windows.
    This prevents accidental clicks from pausing the application.
    """
    if os.name == 'nt':  # Check if the operating system is Windows
        try:
            # Get the handle to the standard input (console input buffer)
            STD_INPUT_HANDLE = -10
            h_console = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)

            # Get the current console mode
            # CONSOLE_MODE_TYPE = ctypes.wintypes.DWORD
            # mode = CONSOLE_MODE_TYPE()
            # ctypes.windll.kernel32.GetConsoleMode(h_console, ctypes.byref(mode))

            # The flags for console input mode.
            # ENABLE_QUICK_EDIT_MODE = 0x0040 (64)
            # ENABLE_EXTENDED_FLAGS = 0x0080 (128) - This flag enables/disables quick edit.
            # ENABLE_INSERT_MODE = 0x0020
            # ENABLE_LINE_INPUT = 0x0002
            # ENABLE_ECHO_INPUT = 0x0004
            # ENABLE_PROCESSED_INPUT = 0x0001
            
            # The desired mode: Enable processed input, line input, echo input, etc.,
            # but *disable* quick edit.
            # The value 0x0080 is often used to *enable* extended flags which includes quick edit.
            # To disable Quick Edit, you typically want to set the mode to exclude the quick edit flag.
            
            # Common flags to keep (from a regular console mode without quick edit):
            # ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT | ENABLE_WINDOW_INPUT | ENABLE_MOUSE_INPUT
            # However, ENABLE_MOUSE_INPUT often includes Quick Edit's functionality implicitly.
            # A common approach to disable it is to specifically *unset* the Quick Edit bit.

            # Let's get the current mode and then clear the Quick Edit bit.
            # Define constants
            ENABLE_QUICK_EDIT_MODE = 0x0040  # This is the flag for Quick Edit Mode
            
            # Get the current console mode
            lpMode = ctypes.wintypes.DWORD()
            ctypes.windll.kernel32.GetConsoleMode(h_console, ctypes.byref(lpMode))
            
            # Disable Quick Edit Mode by clearing its bit
            new_mode = lpMode.value & ~ENABLE_QUICK_EDIT_MODE
            
            # Set the new console mode
            ctypes.windll.kernel32.SetConsoleMode(h_console, new_mode)
            
            # print("Quick Edit Mode disabled for this console.")
            print("Edit Mode disabled for this console.")
        except Exception as e:
            # print(f"Could not disable Quick Edit Mode: {e}")
            print(f"Could not disable Edit Mode: {e}")
            print("You may need to disable it manually in console properties.")
    else:
        print("Quick Edit Mode is a Windows-specific feature. Not applicable on this OS.")

if sys.platform == "win32":
    import win32api
    import win32con

# (Add the logging setup code from step 1 here)

def console_ctrl_handler(ctrl_type):
    global app_logger
    if ctrl_type == win32con.CTRL_C_EVENT:
        # app_logger.warning("CTRL_C_EVENT received! Performing cleanup...")
        # Add your cleanup code here
        return True  # Indicate that we handled the event (prevents default termination)
    elif ctrl_type == win32con.CTRL_BREAK_EVENT:
        # app_logger.warning("CTRL_BREAK_EVENT received! Performing cleanup before exiting...")
        app_logger.warning("CTRL+BREAK event received!")
        # This is where you put your code to save data, close files, etc.
        # You have a limited time to perform cleanup before Windows might force-terminate.
        # app_logger.info("Simulating cleanup for 3 seconds...")
        # time.sleep(3)
        # app_logger.info("Cleanup complete. Exiting gracefully.")
        return False  # Return False to allow the default termination (closing the window)
    elif ctrl_type == win32con.CTRL_CLOSE_EVENT:
        # app_logger.warning("CTRL_CLOSE_EVENT (Close button) clicked! Performing cleanup before exiting...")
        app_logger.warning("CLOSE event received!")
        # app_logger.info("Simulating cleanup for 3 seconds...")
        # time.sleep(3)
        # app_logger.info("Cleanup complete. Exiting gracefully.")
        return False
    elif ctrl_type == win32con.CTRL_LOGOFF_EVENT:
        # app_logger.critical("CTRL_LOGOFF_EVENT received! User logging off. Performing urgent cleanup...")
        app_logger.warning("LOGOFF event received!")
        # Be very quick with cleanup here, system is shutting down/logging off
        return False
    elif ctrl_type == win32con.CTRL_SHUTDOWN_EVENT:
        # app_logger.critical("CTRL_SHUTDOWN_EVENT received! System shutting down. Performing urgent cleanup...")
        app_logger.warning("SHUTDOWN event received!")
        # Be very quick with cleanup here
        return False
    return False # For unhandled events, let the system handle them

if __name__ == '__main__':
    app_logger.info("Application is starting...")

    # Register the console control handler
    if sys.platform == "win32": # Ensure this only runs on Windows
        if win32api.SetConsoleCtrlHandler(console_ctrl_handler, True) == 0:
            app_logger.error("Error: Could not set console control handler.")
            sys.exit(1)
    else:
        app_logger.info("Not on Windows. CTRL_BREAK_EVENT handler will not be active.")

    # app_logger.info("Python console app is running. Try pressing Ctrl+Break, Ctrl+C, or clicking the Close (X) button.")
    app_logger.info("Console app is running...")

    # disable_quick_edit_mode()
    # print("If Quick Edit Mode was successfully disabled, clicking will not pause the application.")

    app_logger.info("Console window start")

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
    # uvicorn.run(app)
