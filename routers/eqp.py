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

@router.post('/get-state')
async def api_get_eqp_state(request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    glogger.info('api_get_eqp_state start')
    login_user = db.query(User).filter(User.id == login_id).first()
    
    # if login_user.acc_type == 'ALL' :
    #     glogger.warning('api_eqp_status : You do not have permission.', 
    #                     {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #     # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
    #     #                     detail='You are not allowed to perform this action')
    #     return {'Success': False,
    #             'State': 'NG',
    #             'ErrorCode': 403,
    #             'Message': 'You do not have permission.'}
    
    try:
        eqp = request.app.state.tsc
        eqp_state = eqp.equipment_state
        # glogger.info(f"api_get_eqp_state : eqp_state={eqp_state}")
    
    except Exception as err:
        glogger.warning(f'api_get_eqp_state : error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
        #                     detail=f'port_no={portno}, {str(err)}')
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    glogger.info(f'api_get_eqp_state : EquipmentState={eqp_state}',
                    {'user': '{},{}'.format(login_user.userid, login_user.name)})

    return {'Success': True,
            'State': 'OK',
            'ErrorCode': 0,
            'Message': '',
            'EquipmentState': eqp_state}

@router.post('/state')
async def api_eqp_state(condition: schemas.EqpInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    glogger.info('api_eqp_state start')
    login_user = db.query(User).filter(User.id == login_id).first()
    
    # if login_user.acc_type == 'ALL' :
    #     glogger.warning('api_eqp_status : You do not have permission.', 
    #                     {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #     # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
    #     #                     detail='You are not allowed to perform this action')
    #     return {'Success': False,
    #             'State': 'NG',
    #             'ErrorCode': 403,
    #             'Message': 'You do not have permission.'}
    
    try:
        eqp = request.app.state.tsc
        eqp_state = eqp.equipment_state
        if condition.eqp_state not in [0, 1, 2, 3]:
            glogger.warning('api_eqp_state : eqp_state {} is not exist.'.format(condition.eqp_state), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 500,
                    'Message': f'eqp_state {condition.eqp_state} is not exist.'}
        eqp.equipment_state = condition.eqp_state
        glogger.info(f"api_eqp_state : prev={eqp_state}, new={eqp.equipment_state}")
        eqp.mqtt_publish_status()
        try:
            tsc = request.app.state.tsc
            for portno in tsc.loadport:
                type = tsc.loadport[portno]['com'].upper()
                if type == 'E84':
                    id = tsc.loadport[portno]['id']
                    tsc.e84[id].run_cmd('status')
                    if settings.RPA:
                        if condition.eqp_state == 3:  # Execute
                            tsc.e84[id].run_cmd('clamp_on')
                        elif condition.eqp_state == 2:  # Idle
                            tsc.e84[id].run_cmd('clamp_off')
                else:
                    if tsc.rfid:
                        tsc.rfid.mqtt_publish_status(portno)
                    if tsc.rfid_UHF:
                        tsc.rfid_UHF.mqtt_publish_status(portno)
        
        except Exception as err:
            # print(str(err))
            # glogger.warning(f'api_eqp_state : exception={str(err)}', 
            #         {'user': '{},{}'.format(login_user.userid, login_user.name)})
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            #                     detail=f'exception={str(err)}')
            glogger.warning('api_eqp_state : loadport error={}'.format(str(err)), 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
            return {'Success': False,
                    'State': 'NG',
                    'ErrorCode': 403,
                    'Message': f'loadport error={str(err)}.'}
    
    except Exception as err:
        glogger.warning(f'api_eqp_state : error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
        #                     detail=f'port_no={portno}, {str(err)}')
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    glogger.info(f'api_eqp_state : EquipmentState={eqp.equipment_state}',
                    {'user': '{},{}'.format(login_user.userid, login_user.name)})

    return {'Success': True,
            'State': 'OK',
            'ErrorCode': 0,
            'Message': '',
            'EquipmentState': eqp.equipment_state}

@router.post('/wafer')
async def api_setting_wafer(condition: schemas.WaferInfo, request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    try:
        glogger = request.app.state.glogger
        glogger.info('api_setting_wafer start')
        login_user = db.query(User).filter(User.id == login_id).first()

        key = 'WAFER_TYPE'
        value = condition.wafer_type    
        # Update the .env file
        set_key('.env', key, value, quote_mode='never')
        settings.WAFER_TYPE = value
        
        glogger.info(f'api_setting_wafer: {key}={value}', 
                    {'user': f'{login_user.userid},{login_user.name}'})
        
        tsc = request.app.state.tsc
        tsc.mqtt_publish_status()
        
        # Reload settings to reflect changes
        # global settings
        # del settings
        # settings = Settings()
        print(f"WAFER_TYPE={settings.WAFER_TYPE}")
        
        # If you need to update the application state
        # request.app.state.settings = settings

        for portno in tsc.loadport:
            if portno == settings.WAFER_TYPE:
                type = tsc.loadport[portno]['com'].upper()
                # dual = tsc.loadport[portno]['dual']
                if type == 'E84':
                    id = tsc.loadport[portno]['id']
                    tsc.e84[id].run_cmd('version')
                    tsc.e84[id].run_cmd('status')
                    # msg = f'E84'
                    # print(f"api_port_initial : port_no = {portno} is E84")
                else:
                    # msg = f'RFID'
                    # print(f"api_port_initial : port_no = {portno} is RFID reader")
                    if tsc.rfid:
                        tsc.rfid.mqtt_publish_status(portno)
                    if tsc.rfid_UHF:
                        tsc.rfid_UHF.mqtt_publish_status(portno)
                break

        return {
            'Success': True,
            'State': 'OK',
            'ErrorCode': 0,
            'Message': 'NG',
        }
        
    except Exception as err:
        glogger.warning(f'api_setting_wafer error: {str(err)}', 
                       {'user': f'{login_user.userid},{login_user.name}'})
        return {
            'Success': False,
            'State': 'NG',
            'ErrorCode': 500,
            'Message': str(err)
        }
    
@router.get('/wafer')
async def api_get_wafer(request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    glogger.info('api_get_wafer start')
    login_user = db.query(User).filter(User.id == login_id).first()
    
    # if login_user.acc_type == 'ALL' :
    #     glogger.warning('api_eqp_status : You do not have permission.', 
    #                     {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #     # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
    #     #                     detail='You are not allowed to perform this action')
    #     return {'Success': False,
    #             'State': 'NG',
    #             'ErrorCode': 403,
    #             'Message': 'You do not have permission.'}
    
    try:
        global settings
        wafer_type = settings.WAFER_TYPE
        # glogger.info(f"api_get_wafer : eqp_state={eqp_state}")
    
    except Exception as err:
        glogger.warning(f'api_get_wafer : error={str(err)}', 
                {'user': '{},{}'.format(login_user.userid, login_user.name)})
        # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
        #                     detail=f'port_no={portno}, {str(err)}')
        return {'Success': False,
                'State': 'NG',
                'ErrorCode': 500,
                'Message': str(err)}
    
    glogger.info(f'api_get_wafer : Wafer Type={wafer_type}',
                    {'user': '{},{}'.format(login_user.userid, login_user.name)})

    return {'Success': True,
            'State': 'OK',
            'ErrorCode': 0,
            'Message': '',
            'WaferType': wafer_type}