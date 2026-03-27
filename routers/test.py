from auth import oauth2, schemas
from fastapi import APIRouter, Depends, HTTPException, status, Request
from database import get_db
from sqlalchemy.orm import Session
from models.user import User #, Permission, AccountType, AccountTypePermission
# from auth import utils
# from sqlalchemy import or_
from collections import OrderedDict
# from global_log import glogger
from config import Settings, settings
from dotenv import set_key
# from fastapi.encoders import jsonable_encoder
from time import time
from event import EventMgr

router = APIRouter()

@router.post('/mqtt-msg')
async def api_ipc_port_mqtt_msg(request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    event_mgr = request.app.state.tsc.event_mgr
    
    # print(request)
    try:
        # req_json = await request.json()
        # print(req_json)
        # body = await request.body() ## will get seems like raw binary data ex: b'"{\\"event\\": \\"Alarm\\", \\"class\\": \\"ALARM\\", ..., \\"spec\\": \\"E84\\"}"'
        # print(body)
        
        data = {}
        data['device_id'] = settings.DEVICE_ID
        data['port_id'] = '1'
        data['port_no'] = 1
        data['dual_port'] = 0
        data['mode'] = 2
        data['carrier_id'] = '123C12345'
        data['type'] = 2
        data['stream'] = -1
        data['function'] = -1
        data['code_id'] = 0
        data['sub_id'] = 1
        data['msg_text'] = 'read rfid'
        data['status'] = ''
        data['occurred_at'] = time()
        event_mgr.on_notify(data)
        
        # return req_json
    



        # msg = {}
        # msg['Success'] = True
        # msg['State'] = 'OK'
        # msg['ErrorCode'] = 0
        # msg['Message'] = 'NA'
        # msg['PortID'] = condition.PortID
        # msg['BoxID'] = condition.BoxID
        # msg['CassetteID'] = ''.join(random.choices('0123456789', k=12))
    except ValueError:
        #log_and_raise(HTTPStatus.BAD_REQUEST, reason="bad JSON body")
        print(ValueError)

    # return jsonable_encoder(msg)
    result = 'OK'
    msg = 'Success'
    return {'Result': result, 'Message': msg}

@router.post('/trigger_plc')
async def api_port_trigger_plc(condition: schemas.PLCInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger

    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('trigger_plc : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning(f'trigger_plc : Do not support port_no = {portno}.', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f'Do not support port_no = {portno}.')

        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            tsc.e84[id].run_cmd('trigger_plc;' + condition.cmd)
            print(f"trigger_plc : {portno}, {condition.cmd}")
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'   
    
    except Exception as err:
        print(str(err))
        glogger.warning(f'trigger_plc : port_no = {portno}, {str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'port_no = {portno}, {str(err)}')

    # "Result": "NG"/"OK",
    # "ErrorCode": 0,
    # "Message": "NA" / "PortID not found"
    return {'Result': result,
            'Message': msg}

@router.post('/event')
async def api_test_event(condition: schemas.TestEventInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    try:
        glogger = request.app.state.glogger
        event_mgr = request.app.state.tsc.event_mgr

        login_user = db.query(User).filter(User.id == login_id).first()
        
        if login_user.acc_type == 'ALL' :
            glogger.warning('api_test_event : 403 You are not allowed to perform this action', {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this action')
            return {'Success': False, 'State': 'NG', 'ErrorCode': 403, 'Message': 'You are not allowed to perform this action'}
        
        data = OrderedDict()
        data['Server'] = True
        data['device_id'] = condition.device_id
        data['port_no'] = condition.port_no
        data['port_id'] = condition.port_id
        data['port_state'] = condition.port_state
        data['carrier_id'] = condition.carrier_id
        data['dual_port'] = condition.dual_port
        data['mode'] = condition.mode # Access Mode 0: Unknown, 1: Auto, 2: Manual
        data['load'] = condition.load #  0071 status
        data['alarm_id'] = condition.alarm_id
        data['alarm_text'] = condition.alarm_text
        data['type'] = condition.type
        data['stream'] = condition.stream
        data['function'] = condition.function
        data['code_id'] = condition.code_id
        data['sub_id'] = condition.sub_id
        data['msg_text'] = condition.msg_text
        data['status'] = condition.status
        data['occurred_at'] = time()
        event_mgr.on_notify(data)

        glogger.info('api_test_event : success, data={}'.format(str(data)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
        return {'Success': True, 'State': 'OK', 'ErrorCode': 0, 'Message': 'NA'}
        
    except Exception as err:
        glogger.error('api_test_event error : {}'.format(str(err)), {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=500, detail="Internal server error")
        return {'Success': False, 'State': 'NG', 'ErrorCode': 500, 'Message': 'Internal server error'}
    
@router.post('/alarm')
async def api_test_alarm(condition: schemas.TestAlarmInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    try:
        glogger = request.app.state.glogger
        event_mgr = request.app.state.tsc.event_mgr

        login_user = db.query(User).filter(User.id == login_id).first()
        
        if login_user.acc_type == 'ALL' :
            glogger.warning('api_test_alarm : 403 You are not allowed to perform this action', {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this action')
            return {'Success': False, 'State': 'NG', 'ErrorCode': 403, 'Message': 'You are not allowed to perform this action'}
        
        data = OrderedDict()
        data['Server'] = True
        data['device_id'] = condition.device_id
        data['port_no'] = condition.port_no
        data['port_id'] = condition.port_id
        data['port_state'] = condition.port_state
        data['carrier_id'] = condition.carrier_id
        data['dual_port'] = condition.dual_port
        data['mode'] = condition.mode # Access Mode 0: Unknown, 1: Auto, 2: Manual
        data['load'] = condition.load #  0071 status
        data['type'] = condition.type
        data['stream'] = condition.stream
        data['function'] = condition.function
        data['code_id'] = condition.code_id
        data['sub_id'] = condition.sub_id
        data['msg_text'] = condition.msg_text
        data['status'] = condition.status
        data['occurred_at'] = time()
        event_mgr.on_notify(data)

        glogger.info('api_test_alarm : success, data={}'.format(str(data)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
        return {'Success': True, 'State': 'OK', 'ErrorCode': 0, 'Message': 'NA'}
        
    except Exception as err:
        glogger.error('api_test_alarm error : {}'.format(str(err)), {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=500, detail="Internal server error")
        return {'Success': False, 'State': 'NG', 'ErrorCode': 500, 'Message': 'Internal server error'}
    
@router.post('/web-service')
async def api_test_web_service(condition: schemas.TestWebServiceInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    try:
        glogger = request.app.state.glogger
        event_mgr = request.app.state.tsc.event_mgr

        login_user = db.query(User).filter(User.id == login_id).first()
        
        if login_user.acc_type == 'ALL' :
            glogger.warning('api_test_web_service : 403 You are not allowed to perform this action', {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this action')
            return {'Success': False, 'State': 'NG', 'ErrorCode': 403, 'Message': 'You are not allowed to perform this action'}
        
        data = OrderedDict()
        data['Server'] = True
        data['device_id'] = condition.device_id
        data['port_no'] = condition.port_no
        data['port_id'] = condition.port_id
        data['port_state'] = condition.port_state
        data['carrier_id'] = condition.carrier_id
        data['dual_port'] = condition.dual_port
        data['mode'] = condition.mode # Access Mode 0: Unknown, 1: Auto, 2: Manual
        data['load'] = condition.load #  0071 status
        data['type'] = condition.type
        data['stream'] = condition.stream
        data['function'] = condition.function
        data['code_id'] = condition.code_id
        data['sub_id'] = condition.sub_id
        data['msg_text'] = condition.msg_text
        data['status'] = condition.status
        data['occurred_at'] = time()
        event_mgr.on_notify(data)

        glogger.info('api_test_web_service : success, data={}'.format(str(data)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
        return {'Success': True, 'State': 'OK', 'ErrorCode': 0, 'Message': 'NA'}
        
    except Exception as err:
        glogger.error('api_test_web_service error : {}'.format(str(err)), {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=500, detail="Internal server error")
        return {'Success': False, 'State': 'NG', 'ErrorCode': 500, 'Message': 'Internal server error'}