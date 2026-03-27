from datetime import datetime
# import uuid
from pydantic import BaseModel, constr
from typing import List, Optional

###### User ######

class UserBaseSchema(BaseModel):
    userid: str
    name: str
    acc_type: str
    active: bool = True

    class Config:
        from_attributes = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    passwordConfirm: str
    #acc_type: str = 'OP'


class LoginUserSchema(BaseModel):
    userid: str
    password: constr(min_length=8)


class UserResponse(UserBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime

    
class ListUserResponse(BaseModel):
    status: str
    results: int
    users: List[UserResponse]
    
class UpdateUserSchema(BaseModel):
    userid: str #| None = None
    name: str #| None = None
    acc_type: str #| None = None
    active: bool #| None = None
    # password: constr(min_length=8) #| None = None

    class Config:
        from_attributes = True

class PermissionResponse(BaseModel):
    code: str
    name: str
    class Config:
        from_attributes = True

class ListPermissionResponse(BaseModel):
    status: str
    results: int
    permissions: List[PermissionResponse]
    
class AccountTypeResponse(BaseModel):
    acc_type: str
    name: str
    class Config:
        from_attributes = True

class ListAccountTypeResponse(BaseModel):
    status: str
    results: int
    account_types: List[AccountTypeResponse]

class AccountTypePermissionResponse(BaseModel):
    code: str
    permission: str
    class Config:
        from_attributes = True

class ListAccountTypePermissionResponse(BaseModel):
    status: str
    results: int
    account_type_permissions: List[AccountTypePermissionResponse]
    
class AllAccountTypePermissionResponse(BaseModel):
    acc_type: str
    code: str
    permission: str
    class Config:
        from_attributes = True

class ListAllAccountTypePermissionResponse(BaseModel):
    status: str
    results: int
    account_type_permissions: List[AllAccountTypePermissionResponse]

###### IPC ######

class IPCBaseSchema(BaseModel):
    device_id: str
    name: str
    group: Optional[str]
    ip: str
    port: int
    ipc_enable: bool = True
    ftp_enable: bool = True

    class Config:
        from_attributes = True

class CreateIPCSchema(IPCBaseSchema):
    pass

class IPCResponse(IPCBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    
class ListIPCResponse(BaseModel):
    status: str
    results: int
    ipcs: List[IPCResponse]
    
class UpdateIPCSchema(IPCBaseSchema):

    class Config:
        from_attributes = True
        
class IPCSelectRequest(BaseModel):
    draw: int
    columns: List[str] = ['device_id', 'name', 'group']
        
class IPCSelectSchema(BaseModel):
    device_id: str
    name: str
    group: str
        
class IPCSelectResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[IPCSelectSchema]
        
# class IPCStatusResponse(IPCBaseSchema):
#     id: int
#     status: str
#     detail: str
    
# class ListIPCStatusResponse(BaseModel):
#     status: str
#     results: int
#     ipc_status: List[IPCStatusResponse]
    
###### Server ######    
class ServerBaseSchema(BaseModel):
    name: str
    ip: str
    port: int
    url: str
    svr_enable: bool = False

    class Config:
        from_attributes = True

class ServerResponse(ServerBaseSchema):
    updated_at: datetime
    
class UpdateServerSchema(ServerBaseSchema):
    pass
    # class Config:
    #     from_attributes = True
    
###### RV Server ######    

class RVServerBaseSchema(BaseModel):
    name: str
    send_subject: str
    listen_subject: str
    rvs_enable: bool = False

    class Config:
        from_attributes = True

class RVServerResponse(RVServerBaseSchema):
    updated_at: datetime
    
class UpdateRVServerSchema(RVServerBaseSchema):
    pass
    # class Config:
    #     from_attributes = True
        
###### FTP ######
class FTPEnable(BaseModel):
    ftp_enable: bool = True
    ipc_enable: bool = False # for GEM300 + SECS/GEM E84IPC version used.
    
class FTPUpdate(BaseModel):
    ip: str
    port: int

class FTPResponse(BaseModel):
    name: str
    ip: str
    port: int
    ftp_enable: bool
    updated_at: datetime

class FTPMode(BaseModel):
    mode: int = 0

###### Log ######

class LogBaseSchema(BaseModel):
    id: int
    event: str
    user: str
    message: str
    type: str
    created_at: datetime

    class Config:
        from_attributes = True
        
class LogResponse(LogBaseSchema):
    pass
        
class ListLogResponse(BaseModel):
    status: str
    results: int
    logs: List[LogResponse]
    
class LogSearchResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[LogResponse]
    
class SearchSchema(BaseModel):
    draw: int = 1
    length: int = 10
    start: int = 0
    search: str = ''
    id: int = 0
    start_id: int = 0
    end_id: int = 0
    start_time: str = ''
    end_time: str = ''
    order_by: str = 'desc'
    order_column: str = 'id'
        
class LogSearchSchema(SearchSchema):
    event: str = ''
    user: str = ''
    message: str = ''
    type: str = ''

class LogFileNameSchema(BaseModel):
    # device_id: str = ''
    # filepath: str = ''
    filename: str = ''

class LogFileSearchSchema(BaseModel):
    draw: int = 1
    length: int = 10
    start: int = 0
    # device_id: str = ''
    search: str = ''
    start_datetime: str = ''
    end_datetime: str = ''
    
class LogFileSchema(BaseModel):
    # filepath: str = ''
    filename: str = ''
    # extension: str = ''
    modified: str = ''
    size: int = 0
    
class LogFilesResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[LogFileSchema]

###### Event ######
    
class EventBaseSchema(BaseModel):
    id: int
    device_id: str
    dataid: int
    ceid: int
    rpt: str
    cause: Optional[str]
    detail: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
class EventResponse(EventBaseSchema):
    pass
        
class ListEventResponse(BaseModel):
    recordsTotal: int
    recordsFiltered: int
    data: List[EventResponse]
    # status: str
    # results: int
    # events: List[EventResponse]
    
class EventSearchResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[EventResponse]
    
class EventSearchSchema(SearchSchema):
    device_id: str = ''
    dataid: int = 0
    ceid: int = 0
    rpt: str = ''
    cause: str = ''
    detail: str = ''
    description: str = ''
    start2_time: str = ''
    end2_time: str = ''

###### Alarm ######
 
class AlarmBaseSchema(BaseModel):
    id: int
    device_id: str
    alcd: int
    alid: int
    altx: str
    level: str
    cause: Optional[str]
    detail: Optional[str]
    description: Optional[str]
    new: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
class AlarmResponse(AlarmBaseSchema):
    pass
        
class ListAlarmResponse(BaseModel):
    status: str
    results: int
    alarms: List[AlarmResponse]
    
class AlarmSearchResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[AlarmResponse]
          
class AlarmSearchSchema(SearchSchema):
    device_id: str = ''
    alcd: int = 0
    alid: int = 0
    altx: str = ''
    level: str = ''
    cause: str = ''
    detail: str = ''
    description: str = ''
    new: int = -1
    start2_time: str = ''
    end2_time: str = ''
    
######## Message ########
 
class MessageBaseSchema(BaseModel):
    sf: str
    code: int
    subcode: int
    msgtext: str
    description: Optional[str]
    argp: bool = False
    ens: bool = False
    eqas: bool = False
    webapi: bool = False
    ftp: bool = False

    class Config:
        from_attributes = True
        
class CreateMessageSchema(MessageBaseSchema):
    pass
        
class MessageResponse(MessageBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    
class UpdateMessageSchema(MessageBaseSchema):
    id: int
        
class ListMessageResponse(BaseModel):
    recordsTotal: int
    recordsFiltered: int
    data: List[MessageResponse]
    
class MessageSearchResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[MessageResponse]
          
class MessageSearchSchema(SearchSchema):
    sf: str = ''
    code: int = -1
    subcode: int = -1
    msgtext: str = ''
    description: str = ''
    start2_time: str = ''
    end2_time: str = ''
    
class ServerMessageSchema(BaseModel):
    type: str = ''
    server: str = ''
    
class ServerMessageBaseSchema(BaseModel):
    id: int
    sf: str
    code: int
    subcode: int
    msgtext: str
    description: str
    enable: bool = False
    
class ListServerMessageResponse(BaseModel):
    recordsTotal: int
    recordsFiltered: int
    data: List[ServerMessageBaseSchema]
    
class ServerMessageSettingSchema(BaseModel):
    id: int
    enable: bool = False
    
class UpdateServerMessageSetting(BaseModel):
    draw: int = 1
    length: int = 1
    server: str = ''
    data: List[ServerMessageSettingSchema]
    
########## Pi Config ##########
class COMPort(BaseModel):
    name: str
    enable: bool = False
    com: int = 1
    device: str
    
class ConfigCOMPort(BaseModel):
    length: int = 1
    setting: List[COMPort]
    
class Network(BaseModel):
    protocol: str
    enable: bool = False
    ip: str = '127.0.0.1'
    port: int = '5000'
    id: str
    name: str
    
class ConfigNetwork(BaseModel):
    length: int = 1
    setting: List[Network]
    
# [Load Port 1]
# Enable = 1
# COM = 1
# RFID = LF

# [Load Port 2]
# Enable = 1
# COM = 2
# RFID = LF

# [Load Port 3]
# Enable = 1
# COM = 3
# RFID = UHF

# [Load Port 4]
# Enable = 1
# COM = 4
# RFID = UHF

# [LF-RFID]
# Enable = 1
# COM = 9

# [UHF-RFID]
# Enable = 0
# COM = 9
    
# [HSMS]
# Enable = 1
# IP = 127.0.0.1
# Port = 5000
# ID = 0
# Name = ABCD01

# [MQTT]
# Enable = 1
# IP = 127.0.0.1
# Port = 1883
# Client ID = ABCD01
# Topic = PiIPC
    
########## Port ##########
    
class PortInfo(BaseModel):
    # device_id: str
    port_no: int = 1
    # port_id: Optional[str]
    enable: Optional[bool]
    
class AlarmInfo(BaseModel):
    port_no: int = 1
    alarm_id: int = 1

class PortCmd(BaseModel):
    # device_id: str
    port_no: int = 1
    # port_id: Optional[str]
    cs: int = 0
    cmd: str
    data: str

########## Equipment ##########
    
class EqpInfo(BaseModel):
    eqp_state: int = 0

class WaferInfo(BaseModel):
    wafer_type: int = 0

class PLCInfo(BaseModel):
    # device_id: str
    port_no: int
    cmd: str

class CSInfo(BaseModel):
    port_no: int = 1
    cs: int = 0

class Handoff(BaseModel):
    port_no: int = 1
    cs: int = 0
    task: int = 0 # 0: load, 1: unload

class TestEventInfo(BaseModel):
    device_id: str
    port_no: int = 1
    port_id: str = 'LP1'
    port_state: int = 1
    carrier_id: str = ''
    dual_port: int = 0
    mode: int = 1 # Access Mode 0: Unknown, 1: Auto, 2: Manual
    load: int = 1
    alarm_id: int = 0
    alarm_text: str = ''
    type: int = 0
    stream: int = -1
    function: int = -1
    code_id: int = 0x71
    sub_id: int = 1
    msg_text: str = 'Ready to Load'
    status: str = '' # {"P": 0, "I": 0, "O": 192, "G": 0, "E": 1}

class TestAlarmInfo(BaseModel):
    device_id: str
    port_no: int = 1
    port_id: str = 'LP1'
    port_state: int = 1
    carrier_id: str = ''
    dual_port: int = 0
    mode: int = 1 # Access Mode 0: Unknown, 1: Auto, 2: Manual
    load: int = 1
    type: int = 0
    stream: int = -1
    function: int = -1
    code_id: int = 128
    sub_id: int = 99
    msg_text: str = 'test alarm'
    status: int = 1

class TestWebServiceInfo(BaseModel):
    TOOL_ID: str='WD-145'
    PORT_ID: str='LP1'
    E84_STATUS: str='Down'
    ALARM_CODE: str='0x000C'
    ALARM_TEXT: str='ENSEVENT~E84_ALARM~FAB_8E~EQStatus~E84_Alarm_KPO-A7_12_#L : 0x000C 0x05 : Unload : CS0 : GO ON->CS_0 ON : ES OFF~E84_Alarm_KPO-A7_12_#L, 0x000C 0x05 : Unload, CS0, GO ON->CS_0 ON : ES OFF~~2~KPO-A7~12~~~7~E84_Alarm_KPO-A7_12_#L, 0x000C 0x05 : Unload, CS0, GO ON->CS_0 ON : ES OFF~~~~~~~0~'
    ISSUSE_TIME: str='20250610 14:30:23'
    SUPPLIER: str='GYRO'
    VERSION: str='2.87'

