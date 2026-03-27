# from pydantic import BaseSettings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
	HOST:str = '0.0.0.0'
	PORT:int = 7007

	AUTH_ENABLE:bool = False
	ACCESS_TOKEN_EXPIRES_IN:int = 180
	REFRESH_TOKEN_EXPIRES_IN:int = 360
	JWT_ALGORITHM:str = 'RS256'

	CLIENT_ORIGIN:str = 'http://localhost:3000'
 
	ENV_FILE_PATH:str = '.env'
	LOG_DIRS:str = 'log'
	LOG_STDOUT:bool = True
	LOG_SQLITE:bool = False
	LOG_0070:bool = True
	LOG_0071:bool = True
	LOG_LEVEL:int = 20
	# SW_VERSION:str = 'v1.14.0804.0'
	# SW_VERSION:str = 'v1.15.0930.0'
	# SW_VERSION:str = 'v1.16.1017.0' # support UHF_SILION
	# SW_VERSION:str = 'v1.17.1021.0' # amend webservice_svc.py for UMC-8E
	#                                 # Fix SILION UHF reader do not read RFID issue caused by different antena port mapping.
	# SW_VERSION:str = 'v1.18.1030.0' # _read_loop
	# SW_VERSION:str = 'v1.19.1104.0' # support Mexicali OCTO Door OPEN/CLOSE by Relay ON/OFF.
	#                                   RPA Robot set eqp API to CLAMP ON/OFF for Idle and Executive
	# SW_VERSION:str = 'v1.19.1107.0' # support ES_ON, ES_OFF
	# SW_VERSION:str = 'v1.20.1110.0' # support MODBUS LED device for E84 VALID_ON to Load/Unload Complete period
	# SW_VERSION:str = 'v1.20.1111.0' # add Relay OFF when Mexicali OCTO Reset/Auto Recover to avoid door remain in LOCK status.
	# SW_VERSION:str = 'v1.20.1111.1' # add LED OFF when Reset/Auto Recover.
	# SW_VERSION:str = 'v1.21.1119.0' # Support Mexicali E84 1 to 1 multiple type loadport.
	# SW_VERSION:str = 'v1.22.1204.0' # Support Mexicali E84 1 to 1 multiple type loadport.
	# SW_VERSION:str = 'v1.23.1209.0' # add Relay OFF, LED OFF when Reset for UMC-8E and FATC.
	# SW_VERSION:str = 'v1.23.1210.0' # add Relay OFF, LED OFF when Reset.
	# SW_VERSION:str = 'v1.24.1219.1' # add 0x71 0x31~0x40 for Skyworks-JP BLO21 Auto mode Door Open/Close status.
	# SW_VERSION:str = 'v1.25.1230.0' # support Mirra Mesa function.
	# SW_VERSION:str = 'v1.26.0102.0' # change Home sensor from IR sensor to loadport sensor.
	# SW_VERSION:str = 'v1.26.0103.0' # Fix do not read 12" Cassette CarrierID issue which caused by assign wrong LF RFID port_no (correct is port_no + cs).
	SW_VERSION:str = 'v1.1.260310.0' # Disable "Tool in Process mode, ignore Home sensor signal" message.
	                                # release for UMC-8S installation.

	LEDBOARD_ENABLE:bool = False
	LEDBOARD_INITIAL:int = 0
	LEDBOARD_RESET:int = 1
	LEDBOARD_MODE:int = 2

	CLAMP_ENABLE:bool = False
	CLAMP_ON:int = 1
	CLAMP_OFF:int = 2
	
	CLAMP_TEST:bool = False
	MEMORY_CHECK:bool = False

	log_secs_preserve:int = 90
	log_api_preserve:int = 90
	log_ipc_preserve:int = 90

	JWT_PRIVATE_KEY:str = 'LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlCT2dJQkFBSkJBSSs3QnZUS0FWdHVQYzEzbEFkVk94TlVmcWxzMm1SVmlQWlJyVFpjd3l4RVhVRGpNaFZuCi9KVHRsd3h2a281T0pBQ1k3dVE0T09wODdiM3NOU3ZNd2xNQ0F3RUFBUUpBYm5LaENOQ0dOSFZGaHJPQ0RCU0IKdmZ2ckRWUzVpZXAwd2h2SGlBUEdjeWV6bjd0U2RweUZ0NEU0QTNXT3VQOXhqenNjTFZyb1pzRmVMUWlqT1JhUwp3UUloQU84MWl2b21iVGhjRkltTFZPbU16Vk52TGxWTW02WE5iS3B4bGh4TlpUTmhBaUVBbWRISlpGM3haWFE0Cm15QnNCeEhLQ3JqOTF6bVFxU0E4bHUvT1ZNTDNSak1DSVFEbDJxOUdtN0lMbS85b0EyaCtXdnZabGxZUlJPR3oKT21lV2lEclR5MUxaUVFJZ2ZGYUlaUWxMU0tkWjJvdXF4MHdwOWVEejBEWklLVzVWaSt6czdMZHRDdUVDSUVGYwo3d21VZ3pPblpzbnU1clBsTDJjZldLTGhFbWwrUVFzOCtkMFBGdXlnCi0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0t'
	JWT_PUBLIC_KEY:str = 'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZ3d0RRWUpLb1pJaHZjTkFRRUJCUUFEU3dBd1NBSkJBSSs3QnZUS0FWdHVQYzEzbEFkVk94TlVmcWxzMm1SVgppUFpSclRaY3d5eEVYVURqTWhWbi9KVHRsd3h2a281T0pBQ1k3dVE0T09wODdiM3NOU3ZNd2xNQ0F3RUFBUT09Ci0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLQ=='

	DEVICE_ID:str ='E84-IPC'
	LOAD_PORT_NUMBER:int =4
	CS_NUMBER:int = 12

	LOAD_PORT_1_ENABLE:bool = False
	LOAD_PORT_1_COM:int = 1
	LOAD_PORT_1_DUAL:int = 0
	LOAD_PORT_1_ID:str = 'LP1'
	LOAD_PORT_1_RFID:str = 'LF'
	LOAD_PORT_1_LED_ID:int = 1
	LOAD_PORT_1_E84_TYPE:int = -1

	LOAD_PORT_2_ENABLE:bool = False
	LOAD_PORT_2_COM:int = 2
	LOAD_PORT_2_DUAL:int = 0
	LOAD_PORT_2_ID:str = 'LP2'
	LOAD_PORT_2_RFID:str = 'LF'
	LOAD_PORT_2_LED_ID:int = 2
	LOAD_PORT_2_E84_TYPE:int = -1

	LOAD_PORT_3_ENABLE:bool = False
	LOAD_PORT_3_COM:int = 3
	LOAD_PORT_3_DUAL:int = 0
	LOAD_PORT_3_ID:str = 'LP3'
	LOAD_PORT_3_RFID:str = 'LF'
	LOAD_PORT_3_LED_ID:int = 3
	LOAD_PORT_3_E84_TYPE:int = -1

	LOAD_PORT_4_ENABLE:bool = False
	LOAD_PORT_4_COM:int = 4
	LOAD_PORT_4_DUAL:int = 0
	LOAD_PORT_4_ID:str = 'LP4'
	LOAD_PORT_4_RFID:str = 'LF'
	LOAD_PORT_4_LED_ID:int = 4
	LOAD_PORT_4_E84_TYPE:int = -1

	E84_RF_SENSOR_ENABLE:bool = False
	E84_RF_SENSOR_COM:int = 9
	E84_RF_SENSOR_COMMUNICATION_MEDIUM:int = 2
	E84_RF_SENSOR_CHANNEL:int = 155
	E84_RF_SENSOR_ID:str = '122'
	E84_RF_SENSOR_PORT:int = 1

	RFID_DEVICE_ONLY:bool = False

	RFID_READ_PS_ENABLE:bool = False
	RFID_READ_PS_TIME:int = 300
	RFID_DEBUG_ENABLE:bool = False
	RFID_CS0_PATTERN:str = r'^[0-9]{2}[0-9A-Z][BC][0-9]{5}$'
	RFID_CS1_PATTERN:str = r'^[0-9]{2}[0-9A-Z][BC][0-9]{5}$'
	RFID_CS0_LENGTH:int = 9
	RFID_CS1_LENGTH:int = 9
	RFID_CS0_ORDER:int = 1
	RFID_CS1_ORDER:int = 1
	MANUAL_MODE_PS_SENSOR_RFID_READ:bool = False
	PL_SENSOR_RFID_READ:bool = False

	LF_RFID_ENABLE:bool = False
	LF_RFID_COM:int = 5

	LF_RFID_TRY_COUNT:int = 2
	LF_RFID_PICK_COUNT:int = 2
	LF_RFID_REGULAR_READ_TIME:int = 0
	LF_RFID_READ_RF_TIMEOUT:int = 5
	LF_RFID_DATA_TYPE:int = 1
	LF_RFID_READ_PAGE_NUMS:int = 2
	LF_RFID_READ_BEEP:int = 1
	LF_RFID_LENGTH:int = 9
	LF_RFID_READ_TIME:int = 1
	LF_RFID_READ_MODE:int = 1
	LF_RFID_DEV_ID:int = 1
	LF_RFID_ORDER:int = 1
	LF_RFID_INITIAL_PAGE:int = 1
	LF_RFID_READ_INTERVAL_TIME:int = 300

	UHF_RFID_ENABLE:bool = False
	UHF_RFID_COM:int = 6
	UHF_RFID_TRY_COUNT:int = 5
	UHF_RFID_PICK_COUNT:int = 3
	UHF_RFID_TIMEOUT:int = 500
	UHF_RFID_TYPE:int = 1 # 0:RegalScan, 1:Silion
	UHF_RFID_DEBUG_ENABLE:bool = False
	UHF_RFID_LENGTH:int = 12
	UHF_RFID_ORDER:int = 1
	UHF_RFID_READ_INTERVAL_TIME:int = 300
	
	HSMS_ENABLE:bool = False
	HSMS_IP:str = '127.0.0.1'
	HSMS_PORT:int = 5000
	HSMS_ID:int = 0
	HSMS_NAME:str = 'ABCD01'

	E84_THREAD_DEBUG_ENABLE:bool = False
	MQTT_DEBUG_ENABLE:bool = False
	MQTT_RFID_MSG_ENABLE:bool = True
	WAFER_TYPE:int = 0 # 0:All, 1:8" 2:12"
	E84_TYPE:int = 0 # 0:andrews, 1:Gyro-E84, 2:Smart-E84
	RPA:bool = False
	DOOR:bool = False
	MULTIPLE_TYPE:bool = False
	DUAL_RFID:bool = False
 
	MQTT_ENABLE:bool = True
	MQTT_IP:str = '127.0.0.1'
	MQTT_PORT:int = 1883
	MQTT_USERNAME:str = 'mcsadmin'
	MQTT_PASSWORD:str = 'gsi5613686'
	MQTT_CLIENT_ID:str = 'ABCD01'
	# MQTT_TOPIC:str = 'MQTT-Ubuntu/IPC'
	# MQTT_TOPIC_SERVER:str = 'MQTT-Ubuntu/Server'
	MQTT_TOPIC:str = 'IPC'
	MQTT_TOPIC_SERVER:str = 'Server'
	MQTT_HEARTBEAT_ENABLE:bool = True
	MQTT_HEARTBEAT_TIME:int = 5

	MQTT_KEEPALIVE:int = 60
	MQTT_QOS:int = 2
	MQTT_CLEAN_SESSION:int = 0
	# MQTT_CLEAN_START=0
	MQTT_CLEAN_START_FIRST_ONLY:int = 3
	MQTT_TRANSPORT:str = 'tcp'
	# MQTT_TRANSPORT:str = 'websockets'
	MQTT_PROTOCOL:int = 5
	# MQTTv31 = 3
	# MQTTv311 = 4
	# MQTTv5 = 5

	FTP_ENABLE:bool = False
	FTP_IP:str = '192.168.0.248'
	FTP_PORT:int = 21
	FTP_CWD:str = '/log/'
	FTP_USERNAME:str = 'admin'
	FTP_PASSWORD:str = 'root1234'
	FTP_USER_ENABLE:bool = False
	FTP_USER_ALARM_MODE:int = 5

	WEB_SERVICE_ENABLE:bool = False
	WEB_SERVICE_IP:str = '192.168.0.248'
	WEB_SERVICE_PORT:int = 8000
	WEB_SERVICE_URL:str = '/E84_WRS/E84_WRS.asmx?WSDL'
	WEB_SERVICE_TIMEOUT:int = 300
	WEB_SERVICE_DEBUG_ENABLE:bool = False
	WEB_SERVICE_CRITICAL_ALARM:bool = True

	# UMC-8E used for start TP3 LED board
	LED_ENABLE:bool = False
	LED_COM:int = 15
	LED_Address:int = 1

	# UMC-SG used for Stocker Control Panel push button's PLC device 
	API_ENABLE:bool = False
	API_IP:str = '127.0.0.1'
	API_PORT:int = 7007
	API_URL:str = '/INPUTCOMMAND'
 
	UMC_FAB:str = 'FAB_8S'

	model_config = SettingsConfigDict(
        env_file="env.ini",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
  
settings = Settings()
