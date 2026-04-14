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
from fastapi.encoders import jsonable_encoder
from time import time
import json

router = APIRouter()

@router.post('/status')
async def api_port_status(condition: schemas.PortInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    glogger.warning('api_port_status : PortID={}'.format(condition.port_no))
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_status : port_no={}. You do not have permission.'.format(condition.port_no), 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_status : port_no {} is not exist.'.format(condition.port_no), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {condition.port_no} is not exist.'}
        
        status = 0
        port_id = ''
        mode = 0
        alarm_id= 0 
        alarm_text = ''
        carrier_id = ''
        status_msg = ''
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            print(f'###### inside E84 {id}')
            
            # if tsc.loadport[portno]['dual'] == 1:
            #     status_msg = tsc.e84[id].port_status_msg2
            #     status = tsc.e84[id].port_status2
            # else:
            #     status_msg = tsc.e84[id].port_status_msg
            #     status = tsc.e84[id].port_status
            cs = portno-1
            port_id = tsc.e84[id].port_id[cs]
            mode = tsc.e84[id].mode[cs]
            status_msg = tsc.e84[id].port_status_msg[cs]
            status = tsc.e84[id].port_status[cs]
            print(f"port {portno} : port_state= {status}, {status_msg}")
            alarm_text = tsc.e84[id].alarm_text[cs]
            alarm_id = tsc.e84[id].alarm_id[cs]
            print(f"alarm {portno} : id= {alarm_id}, {alarm_text}")

            # result = status if alarm_id == 0 else 6

            # if tsc.loadport[portno]['dual'] == 1:
            #     carrier_id = tsc.e84[id].rfid_data2
            # else:
            #     carrier_id = tsc.e84[id].rfid_data
                
            if not carrier_id:
                carrier_id = ''

                print(f'port_no {portno} : {carrier_id}')
                
        elif tsc.loadport[portno]['com'] == 'rfid':
            id = tsc.loadport[portno]['id']
            print(f"###### inside RFID {id}, {tsc.loadport[portno]['type']}")
            if tsc.loadport[portno]['type'] == 'LF':
                if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    carrier_id = tsc.rfid.rfids[id]
                    if not carrier_id:
                        carrier_id = ''
            elif tsc.loadport[portno]['type'] == 'UHF':
                if settings.LF_RFID_ENABLE or settings.UHF_RFID_ENABLE:
                    carrier_id = tsc.rfid_UHF.rfids[id]
                    if not carrier_id:
                        carrier_id = ''

                    print(f'port_no {portno} : {carrier_id}')

        glogger.info(f'api_port_status : PortID={portno}, PortState={status}, CassetteID={carrier_id}, ErrorCode={alarm_id}, Message={status_msg}, AlarmID={alarm_id}, AlarmText={alarm_text}',
                    {'user': '{},{}'.format(login_user.userid, login_user.name)})
    
    except Exception as err:
        glogger.warning(f'api_port_status : port_no={portno}, error={str(err)}', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': True,
            'State': 'OK',
            'ErrorCode': alarm_id,
            'Message': status_msg,
            # 'PortID': port_id,
            'Mode': mode,
            'PortState': status,
            # 'CarrierID': carrier_id,
            'AlarmID': alarm_id,
            'AlarmText': alarm_text,
            }

@router.post('/alarm-reset')
async def api_port_alarm_reset(condition: schemas.PortInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger

    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_alarm_reset : port_no={}. You do not have permission.'.format(condition.port_no),
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_alarm_reset : port_no {} is not exist.'.format(condition.port_no), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {condition.port_no} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            print(f"id={id}, len={len(tsc.e84)}")
            success = await tsc.e84[id].alarm_reset_async()

            if not success:
                result = 'NG'
                msg = 'E84 alarm reset failed. Device is not connected or did not respond.'
                glogger.warning('api_port_alarm_reset : port_no {} {}'.format(portno, msg), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})

            print(f"api_port_alarm_reset : {portno}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    

    except Exception as err:
        glogger.warning(f'api_port_alarm_reset : port_no={portno}, error={str(err)}', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}

    return {'Success': result == 'OK',
            'State': result,
            'ErrorCode': 0 if result == 'OK' else 500,
            'Message': "" if result == 'OK' else msg}

@router.post('/channel')
async def api_port_channel(condition: schemas.PortInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_channel : You do not have permission.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_channel : port_no {} is not exist.'.format(portno), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {portno} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            dual = '2' if tsc.loadport[portno]['dual'] > 0 else ''
            # print(f"dual={dual}")
            if condition.enable:
                tsc.e84[id].run_cmd(f'channel')
            else:
                tsc.e84[id].run_cmd(f'alarm_reset')
    
            print(f"api_port_channel : {portno}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    
    
    except Exception as err:
        glogger.warning(f'api_port_channel : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': True,
            'State': result,
            'ErrorCode': 0,
            'Message': ""}

# @router.post('/continue')
async def api_port_continue(condition: schemas.PortInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_continue : You do not have permission.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_continue : port_no {} is not exist.'.format(portno), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {portno} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            dual = '2' if tsc.loadport[portno]['dual'] > 0 else ''
            # print(f"dual={dual}")
            tsc.e84[id].run_cmd(f'continue')
    
            print(f"api_port_continue : {portno}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    
    
    except Exception as err:
        glogger.warning(f'api_port_continue : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': True,
            'State': result,
            'ErrorCode': 0,
            'Message': ""}

# @router.post('/cs')
async def api_port_cs(condition: schemas.CSInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_cs : You do not have permission.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_cs : port_no {} is not exist.'.format(portno), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {portno} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            dual = '2' if tsc.loadport[portno]['dual'] > 0 else ''
            # print(f"dual={dual}")
            tsc.e84[id].run_cmd(f'cs {condition.cs}')

            print(f"api_port_cs : {portno}, {condition.cs}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    
    
    except Exception as err:
        glogger.warning(f'api_port_cs : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': True,
            'State': result,
            'ErrorCode': 0,
            'Message': ""}

@router.post('/handoff')
async def api_port_handoff(condition: schemas.Handoff, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_handoff : You do not have permission.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_handoff : port_no {} is not exist.'.format(portno), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {portno} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            dual = '2' if tsc.loadport[portno]['dual'] > 0 else ''
            # print(f"dual={dual}")
            tsc.e84[id].run_cmd(f'handoff {condition.cs} {condition.task}')

            print(f"api_port_handoff : {portno}, {condition.cs}, {condition.task}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    
    
    except Exception as err:
        glogger.warning(f'api_port_handoff : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': True,
            'State': result,
            'ErrorCode': 0,
            'Message': ""}

@router.post('/arm-back')
async def api_port_arm_back(condition: schemas.PortInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_arm_back : You do not have permission.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    result = 'OK'
    msg = 'Success'
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_arm_back : port_no {} is not exist.'.format(portno), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {portno} is not exist.'}
    
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            e84_port = tsc.e84[id]
            e84_client = getattr(e84_port, 'e84', None)

            if e84_client is None:
                result = 'NG'
                msg = 'E84 arm back failed. Device is not ready.'
            else:
                ensure_connected = getattr(e84_port, '_ensure_e84_connected', None)
                if callable(ensure_connected):
                    connected = await ensure_connected("api_port_arm_back")
                else:
                    connected = getattr(getattr(e84_client, '_state', None), 'value', None) == "connected"
                    if not connected:
                        await e84_client.connect_async()
                        connected = getattr(getattr(e84_client, '_state', None), 'value', None) == "connected"

                if not connected:
                    result = 'NG'
                    msg = 'E84 arm back failed. Device is not connected.'
                elif not e84_client._can_send_arm_back():
                    result = 'NG'
                    msg = 'E84 arm back failed. Wait for Load Complete or Unload Complete before calling /arm-back.'
                else:
                    success = await e84_client.arm_back_complete(is_unload=True, ready_timeout=0.0)
                    if not success:
                        result = 'NG'
                        msg = 'E84 arm back failed. Device is not connected or did not respond.'

            if result == 'NG':
                glogger.warning('api_port_arm_back : port_no {} {}'.format(portno, msg),
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})

            print(f"api_port_arm_back : {portno}") 
        else:
            result = 'NG'
            msg = 'RFID reader do not support this command.'    
    
    except Exception as err:
        glogger.warning(f'api_port_arm_back : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    return {'Success': result == 'OK',
            'State': result,
            'ErrorCode': 0 if result == 'OK' else 500,
            'Message': "" if result == 'OK' else msg}

@router.post('/cmd')
async def api_port_cmd(condition: schemas.PortCmd, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    glogger.warning('api_port_cmd : PortID={}'.format(condition.port_no))
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_port_cmd : port_no={}. You do not have permission.'.format(condition.port_no), 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 403,
                'Message': 'You do not have permission.'}
    
    try:
        portno = condition.port_no
        tsc = request.app.state.tsc
        if portno not in tsc.loadport:
            glogger.warning('api_port_cmd : port_no {} is not exist.'.format(condition.port_no), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'Do not support port_no={portno}.')
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'port_no {condition.port_no} is not exist.'}
        
        result = 0
        if tsc.loadport[portno]['com'] == 'e84':
            id = tsc.loadport[portno]['id']
            tsc.e84[id].run_cmd2(condition.cs, condition.cmd, condition.data)
            
        elif tsc.loadport[portno]['com'] == 'rfid':
            glogger.error(f'api_port_cmd : port_no={portno} is not E84 controller')
    
    except Exception as err:
        glogger.warning(f'api_port_cmd : port_no={portno}, error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    glogger.warning(f'api_port_cmd : PortID={portno}, ErrorCode="", Message=""',
                    {'user': '{},{}'.format(login_user.userid, login_user.name)})

    # return {'Result': 'OK',
    return {'Success': True,
            'State': 'OK',
            'ErrorCode': '',
            'Message': '',
            'PortID': portno}
