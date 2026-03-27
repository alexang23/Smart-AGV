from auth import oauth2, schemas
from fastapi import APIRouter, Depends, HTTPException, status, Request
from database import get_db
from sqlalchemy.orm import Session
from models.user import User #, Permission, AccountType, AccountTypePermission
# from auth import utils
# from sqlalchemy import or_
from global_log import glogger
from config import Settings, settings
from dotenv import set_key

router = APIRouter()

def update_env_file(name, value):
    global settings
    
    mode = 'never'
    fvalue = value
    try:
        if type(value) == bool:
            fvalue = (1 if value else 0)
        elif type(value) == str:
            mode = 'always'
            
        setattr(settings, name, value)
        set_key(dotenv_path=settings.ENV_FILE_PATH, key_to_set=name, value_to_set=fvalue, quote_mode=mode) # one of always, auto or never in set_key
    
    except Exception as e:
        print(str(e))
        # glogger.error('api_update_user error : {}'.format(str(e)), 
        #                 {'user': '{},{}'.format(login_user.userid, login_user.name)})
        return {'result':str(e)}
    
def update_env_file_by_dict(config):
    global settings
    if config == None:
        return
    
    for name, value in config:
    
        mode = 'never'
        fvalue = value
        try:
            if type(value) == bool:
                fvalue = (1 if value else 0)
            elif type(value) == str:
                mode = 'always'
                
            # settings[name] = value
            set_key(dotenv_path=settings.ENV_FILE_PATH, key_to_set=name, value_to_set=fvalue, quote_mode=mode) # one of always, auto or never in set_key
        
        except Exception as e:
            print(str(e))
            # glogger.error('api_update_user error : {}'.format(str(e)), 
            #                 {'user': '{},{}'.format(login_user.userid, login_user.name)})
            return {'result':str(e)}

@router.get('/comport', response_model=schemas.ConfigCOMPort)
async def api_get_comport_config(db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    login_user = db.query(User).filter(User.id == login_id).first()

    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_all_user : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    global settings
    config = settings.dict()
    
    settinglist = []
    for port in range(4):
        name = f'LOAD_PORT_{str(port+1)}' 
        enable = config[name+'_ENABLE']
        com = config[name+'_COM']
        device = config[name+'_RFID']
        print(f'{name} : {enable}, com={com}, {device}')
        settinglist.append(schemas.COMPort(name=name, enable=enable, com=com, device=device))
        
    name = 'LF_RFID'
    enable = config[name+'_ENABLE']
    com = config[name+'_COM']
    device = 'LF'
    print(f'{name} : {enable}, com={com}, {device}')
    settinglist.append(schemas.COMPort(name=name, enable=enable, com=com, device=device))
    
    name = 'UHF_RFID'
    enable = config[name+'_ENABLE']
    com = config[name+'_COM']
    device = 'UHF'
    print(f'{name} : {enable}, com={com}, {device}')
    settinglist.append(schemas.COMPort(name=name, enable=enable, com=com, device=device))
    
    # users = db.query(User).all()
    # glogger.info('api_get_all_user : {}'.format(len(users)), {'user': '{},{}'.format(login_user.userid, login_user.name)})
    return {'length': len(settinglist), 'setting': settinglist}

# @router.put('/comport', response_model=schemas.ConfigCOMPort)
@router.put('/comport')
def api_update_comport_config(payload: schemas.ConfigCOMPort, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    login_user = db.query(User).filter(User.id == login_id).first()

    if login_user.acc_type == 'ALL' :
        glogger.warning('api_update_comport_config : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    global settings
    config = settings.dict()
    # print(settings)
    
    print(payload.length)
    for cfg in payload.setting:
        print(f"new : {cfg}")
        try:
            if (config[cfg.name+'_ENABLE'] != cfg.enable):
                print('enable changed !!')
                name = cfg.name+'_ENABLE'
                value = 1 if cfg.enable else 0
                # config[name] = value
                update_env_file(name, value)
            if (config[cfg.name+'_COM'] != cfg.com):
                print('com changed !!')
                name = cfg.name+'_COM'
                value = cfg.com
                # config[name] = value
                update_env_file(name, value)
            if 'LOAD_PORT' in cfg.name:
                if (config[cfg.name+'_RFID'] != cfg.device):
                    print('rfid changed !!')
                    name = cfg.name+'_RFID'
                    value = cfg.device
                    # config[name] = value
                    update_env_file(name, value)

        except Exception as err:
            print(str(err))
            # glogger.error('api_update_user error : {}'.format(str(e)), 
            #                 {'user': '{},{}'.format(login_user.userid, login_user.name)})
            return {'result':str(err)}
    
    # print(settings)

    return {'result':'success'}

@router.get('/network', response_model=schemas.ConfigNetwork)
async def api_get_network_config(db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_all_user : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    config = settings.dict()
    
    settinglist = []
        
    protocol = 'HSMS'
    enable = config[protocol+'_ENABLE']
    ip = config[protocol+'_IP']
    port = config[protocol+'_PORT']
    id = config[protocol+'_ID']
    name = config[protocol+'_NAME']
    print(f'{protocol} : {enable}, {ip}:{port}, {id}, {name}')
    settinglist.append(schemas.Network(protocol=protocol, enable=enable, ip=ip, port=port, id=id, name=name))
    
    protocol = 'MQTT'
    enable = config[protocol+'_ENABLE']
    ip = config[protocol+'_IP']
    port = config[protocol+'_PORT']
    id = config[protocol+'_CLIENT_ID']
    name = config[protocol+'_TOPIC']
    print(f'{protocol} : {enable}, {ip}:{port}, {id}, {name}')
    settinglist.append(schemas.Network(protocol=protocol, enable=enable, ip=ip, port=port, id=id, name=name))
    
    # users = db.query(User).all()
    # glogger.info('api_get_all_user : {}'.format(len(users)), {'user': '{},{}'.format(login_user.userid, login_user.name)})
    return {'length': len(settinglist), 'setting': settinglist}

# @router.put('/network', response_model=schemas.ConfigNetwork)
@router.put('/network')
def api_update_network_config(payload: schemas.ConfigNetwork, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    login_user = db.query(User).filter(User.id == login_id).first()

    if login_user.acc_type == 'ALL' :
        glogger.warning('api_update_comport_config : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    global settings
    config = settings.dict()
    # print(settings)
    
    print(payload.length)
    for cfg in payload.setting:
        print(f"new : {cfg}")
        
        try:
            if (config[cfg.protocol+'_ENABLE'] != cfg.enable):
                print('enable changed !!')
                name = cfg.protocol+'_ENABLE'
                value = 1 if cfg.enable else 0
                # config[name] = value
                update_env_file(name, value)
            if (config[cfg.protocol+'_IP'] != cfg.ip):
                print('IP changed !!')
                name = cfg.protocol+'_IP'
                value = cfg.ip
                # config[name] = value
                update_env_file(name, value)
            if (config[cfg.protocol+'_PORT'] != cfg.port):
                print('PORT changed !!')
                name = cfg.protocol+'_PORT'
                value = cfg.port
                # config[name] = value
                update_env_file(name, value)
            if 'HSMS' in cfg.protocol:
                if (config[cfg.protocol+'_ID'] != cfg.id):
                    print('ID changed !!')
                    name = cfg.protocol+'_ID'
                    value = cfg.id
                    # config[name] = value
                    update_env_file(name, value)
                if (config[cfg.protocol+'_NAME'] != cfg.name):
                    print('NAME changed !!')
                    name = cfg.protocol+'_NAME'
                    value = cfg.name
                    # config[name] = value
                    update_env_file(name, value)
            elif 'MQTT' in cfg.protocol:
                if (config[cfg.protocol+'_CLIENT_ID'] != cfg.id):
                    print('CLIENT_ID changed !!')
                    name = cfg.protocol+'_CLIENT_ID'
                    value = cfg.id
                    # config[name] = value
                    update_env_file(name, value)
                if (config[cfg.protocol+'_TOPIC'] != cfg.name):
                    print('TOPIC changed !!')
                    name = cfg.protocol+'_TOPIC'
                    value = cfg.name
                    # config[name] = value
                    update_env_file(name, value)

        except Exception as err:
            print(str(err))
            # glogger.error('api_update_user error : {}'.format(str(e)), 
            #                 {'user': '{},{}'.format(login_user.userid, login_user.name)})
            return {'result':str(err)}
    
    # print(settings)
    
    return {'result':'success'}
