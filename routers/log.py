from auth import oauth2, schemas
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from database import get_db
from config import settings
from sqlalchemy.orm import Session
# from sqlalchemy.orm import class_mapper
from models.user import User
from models.log import Log
from models.ipc import IPC
# from ..auth import utils
from sqlalchemy import or_
from datetime import datetime
# from backend.event_center import EventCenter as EC
# from backend.controller_mgr import ControllerMgr as CM
# from collections import OrderedDict
from global_log import glogger
# from global_log import console_logger
import ntpath
import os
from os.path import join, splitext, isdir, basename
# from pathlib import Path
from fastapi.responses import FileResponse
import shutil
import tempfile
from starlette.background import BackgroundTask # Note the import location
# import requests
import traceback
import json
from fastapi.encoders import jsonable_encoder

router = APIRouter()

# list all log records with GET method
@router.get('/all', response_model=schemas.ListLogResponse)
async def api_get_all_log(request: Request, db: Session = Depends(get_db), login_id: str = Depends(oauth2.require_user)):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()

    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_all_log : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    logs = db.query(Log).all()
    glogger.info('api_get_all_log : {}'.format(len(logs)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
    return {'status': 'success', 'results': len(logs), 'logs': logs}

# list all log records with GET conditions method
# @router.get('/list', response_model=schemas.ListLogResponse)
async def api_get_log_list0(
        request: Request,
        db: Session = Depends(get_db),
        login_id: str = Depends(oauth2.require_user),
        limit: int = 10,
        offset: int = 1,
        search: str = '',
        id: int = 0,
        start_id: int = 0,
        end_id: int = 0,
        event: str = '',
        user: str = '',
        message: str = '',
        type: str = '',
        start_time: str = '',
        end_time: str = ''
    ):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()
    skip = (offset - 1) * limit
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_log_list : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
        
    filters = []
    if search :
        filters.append(
            or_(
                Log.event.contains(search),
                Log.user.contains(search),
                Log.message.contains(search),
                Log.type.contains(search),
                Log.created_at.contains(search)
            )
        )
    if event :
        filters.append(Log.event.contains(event))
    if user :
        filters.append(Log.user.contains(user))
    if message :
        filters.append(Log.message.contains(message))
    if type :
        filters.append(Log.type.contains(type))
    
    if start_id > 0 :
        filters.append(Log.id >= start_id)
    if end_id > 0 :
        filters.append(Log.id <= end_id)
    if start_id == 0 and end_id == 0 and id > 0 :
        filters.append(Log.id == id)
        
    if start_time :
        filters.append(Log.created_at >= datetime.strptime(start_time, '%Y-%m-%d %H:%M'))
    if end_time :
        filters.append(Log.created_at <= datetime.strptime(end_time, '%Y-%m-%d %H:%M'))
        
    loglist = db.query(Log).filter(*filters).order_by(Log.id.desc()).limit(limit).offset(skip).all()
    
    glogger.info('api_get_log_list : {}'.format(len(loglist)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
    return {'status': 'success', 'results': len(loglist), 'logs': loglist}

# list all log records with POST conditions method
@router.post('/list', response_model=schemas.LogSearchResponse)
async def api_get_log_list(
        request: Request,
        condition: schemas.LogSearchSchema,
        db: Session = Depends(get_db),
        login_id: str = Depends(oauth2.require_user),
    ):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()
    skip = condition.start # * condition.length
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_log_list : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
        
    filters = []
    if condition.search :
        filters.append(
            or_(
                Log.event.contains(condition.search),
                Log.user.contains(condition.search),
                Log.message.contains(condition.search),
                Log.type.contains(condition.search),
                Log.created_at.contains(condition.search)
            )
        )
    if condition.event :
        filters.append(Log.event.contains(condition.event))
    if condition.user :
        filters.append(Log.user.contains(condition.user))
    if condition.message :
        filters.append(Log.message.contains(condition.message))
    if condition.type :
        filters.append(Log.type.contains(condition.type))
    
    if condition.start_id > 0 :
        filters.append(Log.id >= condition.start_id)
    if condition.end_id > 0 :
        filters.append(Log.id <= condition.end_id)
    if condition.start_id == 0 and condition.end_id == 0 and condition.id > 0 :
        filters.append(Log.id == condition.id)
        
    if condition.start_time :
        filters.append(Log.created_at >= datetime.strptime(condition.start_time, '%Y-%m-%d %H:%M'))
    if condition.end_time :
        filters.append(Log.created_at <= datetime.strptime(condition.end_time, '%Y-%m-%d %H:%M'))
        
    try:
        total = db.query(Log).filter(*filters).order_by(getattr(getattr(Log, condition.order_column), condition.order_by)()).count()
        loglist = db.query(Log).filter(*filters).order_by(getattr(getattr(Log, condition.order_column), condition.order_by)()).offset(skip).limit(condition.length).all()
    except Exception as e:
        #db.rollback()
        glogger.error('api_get_log_list error : {}'.format(str(e)))
        return str(e), 400
    
    glogger.info('api_get_log_list : {}'.format(len(loglist)), {'user': '{},{}'.format(login_user.userid,login_user.name)})
    return {'draw': condition.draw, 'recordsTotal': total, 'recordsFiltered': total, 'data': loglist}

def logfiles_superuser_login(ipc_ip, api_port):
    return
    message = {}
    message['userid'] = "gyro"
    message['password'] = "gsi5613686"
    
    response = {}
    response['result'] = 'NG'

    res = None
    try:
        res = requests.post('http://{}:{}/api/auth/login'.format(ipc_ip, api_port), json=message, timeout=5)
    except requests.ConnectionError:
        glogger.error('logfiles_superuser_login error : requests.ConnectionError')
        response['status_code'] = 503
        response['reason'] = 'requests.ConnectionError'
        return response
    except requests.Timeout:
        glogger.error('logfiles_superuser_login error : requests.Timeout')
        response['status_code'] = 408
        response['reason'] = 'requests.Timeout'
        return response
    except Exception as err:
        glogger.error('logfiles_superuser_login error : {}'.format(str(err)))
        response['status_code'] = 400
        response['reason'] = str(err)
        return response
    
    #print('requests.post : [{}] {}'.format(res.status_code, res.text))
    response['status_code'] = res.status_code
    response['reason'] = res.reason
    #print(response)
    
    if res.status_code == 200 :
        response['result'] = 'success'
        response['access_token'] = json.loads(res.text)['access_token']
        #print(access_token)

    return response

@router.post('/files/list', response_model=schemas.LogFilesResponse)
async def api_get_log_file_list(
        request: Request, 
        condition: schemas.LogFileSearchSchema,
        db: Session = Depends(get_db),
        login_id: str = Depends(oauth2.require_user),
    ):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()
    skip = condition.start # * condition.length
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_get_log_file_list : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    bSearch = False
    bStartDateTime = False
    bEndDateTime = False
    search = ''
    start_timestamp = 0
    end_timestamp = 0
    # console_logger.info(condition)
    if len(condition.search.strip()) > 0 :
        bSearch = True
        search = condition.search.strip()
    if len(condition.start_datetime.strip()) > 0 :
        bStartDateTime = True
        start_timestamp  = datetime.timestamp(datetime.strptime(condition.start_datetime.strip(), '%Y-%m-%d %H:%M'))
        # start_timestamp  = datetime.timestamp(datetime.strptime(condition.start_datetime.strip(), '%Y-%m-%d'))
        # console_logger.info(f'start_timestamp : {condition.start_datetime.strip()} : {start_timestamp}')
    if len(condition.end_datetime.strip()) > 0 :
        bEndDateTime = True
        end_timestamp   = datetime.timestamp(datetime.strptime(condition.end_datetime.strip(), '%Y-%m-%d %H:%M'))# + timedelta(days=1))
        # end_timestamp   = datetime.timestamp(datetime.strptime(condition.end_datetime.strip(), '%Y-%m-%d'))# + timedelta(days=1))
        # console_logger.info(f'end_timestamp : {condition.end_datetime.strip()} : {end_timestamp}')
    filelist = []
    # if len(condition.device_id.strip()) == 0 :
    if settings.LOG_DIRS:
        dirs = settings.LOG_DIRS.split(',')

        for dir in dirs:
            # if isdir(join(os.getenv('HOME'), d)):
            if isdir(dir):
                # filelist = filelist + [{
                #     'filepath': str(entry),
                #     'filename': ntpath.basename(entry),
                #     'extension': splitext(ntpath.basename(entry))[1],
                #     'modified': entry.stat().st_mtime * 1000,
                #     'size': entry.stat().st_size
                # } for entry in Path(dir).iterdir() if entry.is_file()]
                # # } for entry in Path(join(os.getenv('HOME'), dir)).iterdir() if entry.is_file()]

                # Get a list of files in the directory with their modification times
                files_and_modtimes = []

                # for root, _, files in os.walk(dir):
                for root, subdirs, files in os.walk(dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        modtime = os.path.getmtime(file_path)
                        files_and_modtimes.append((file_path, modtime))

                # Sort the list of files based on modification time
                sorted_files = sorted(files_and_modtimes, key=lambda x: x[1], reverse=True)

                # Enumerate and print the sorted files
                for index, (filepath, modified_time) in enumerate(sorted_files, start=1):
                    modtime_datetime = datetime.fromtimestamp(modified_time)
                    # print(f"{index}. {filepath} - Last Modified: {modtime_datetime}")
                
                # for rootdir, subdirs, files in os.walk(dir):
                    # print('~~~~~~')
                    # for subdir in subdirs:
                    #     print('{} ****'.format(os.path.join(rootdir, subdir)))
                    # print('------')
                    # for file in files:
                    #     path = os.path.join(rootdir, file)
                    #     # print(path)
                    #     # print(file)
                    #     ext = os.path.splitext(ntpath.basename(path))[1].lower()
                    #     if ext == '.log' or ext == '.txt' or '.log' in file.lower() :
                    file = os.path.basename(filepath)
                    if '.log' in file.lower() or '.txt' in file.lower():
                        bFilename = False
                        bFilenameDate = False
                        bModified = False
                        bModifiedDate = False

                        if bSearch :
                            if search in file :
                                bFilename = True
                        
                        # modified_time = os.path.getmtime(path)
                        # print('modified_time : {} : {}'.format(path, datetime.fromtimestamp(modified_time)))
                        str_modified_time = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d')
                        if bSearch :
                            if search in str_modified_time :
                                bModified = True
                        # if bStartDateTime :
                        #     if modified_time < start_timestamp :
                        #         continue
                        # if bEndDateTime :
                        #     if end_timestamp < modified_time :
                        #         continue
                        if bStartDateTime and not bEndDateTime:
                            if start_timestamp <= modified_time :
                                bModifiedDate = True
                        if not bStartDateTime and bEndDateTime:
                            if modified_time <= end_timestamp :
                                bModifiedDate = True
                        if bStartDateTime and bEndDateTime:
                            if start_timestamp <= modified_time and modified_time <= end_timestamp :
                                bModifiedDate = True

                        fname = file.split('.log.')
                        # print(fname)
                        if len(fname) > 1:
                            save_time  = datetime.timestamp(datetime.strptime(fname[1].strip(), '%Y-%m-%d'))
                            if bStartDateTime and not bEndDateTime:
                                if start_timestamp <= save_time :
                                    bFilenameDate = True
                            if not bStartDateTime and bEndDateTime:
                                if save_time <= end_timestamp :
                                    bFilenameDate = True
                            if bStartDateTime and bEndDateTime:
                                if start_timestamp <= save_time and save_time <= end_timestamp :
                                    bFilenameDate = True

                        if bSearch :
                            if not (bFilename or bModified):
                                continue

                        if bStartDateTime or bEndDateTime:
                            if not (bFilenameDate or bModifiedDate):
                                continue

                        print(filepath)
                        # print('filepath: {}, filename: {}, extension: {}, modified: {}, size: {}'.format(
                        #         str(path),
                        #         ntpath.basename(path),
                        #         os.path.splitext(ntpath.basename(path))[1],
                        #         os.stat(path).st_mtime * 1000,
                        #         os.stat(path).st_size
                        #     ))
                        # console_logger.info('os.stat.st_mtime {} : {} : {} : {}'.format(path, datetime.fromtimestamp(os.stat(path).st_mtime).strftime("%Y-%m-%d %H:%M:%S"), datetime.fromtimestamp(start_timestamp).strftime("%Y-%m-%d %H:%M:%S"), datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")))
                        filelist.append({
                            # 'filepath': str(rootdir), # str(path),
                            'filename': ntpath.basename(filepath),
                            # 'extension': splitext(ntpath.basename(path))[1],
                            'modified': datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M:%S"),
                            'size': os.stat(filepath).st_size
                            })
    # print(filelist)
    # else :
    #     return
    #     ipc = db.query(IPC).filter(IPC.device_id == condition.device_id).first()
        
    #     if not ipc:
    #         glogger.warning('api_get_log_file_list : No IPC with this device_id {} found.'.format(condition.device_id), 
    #                         {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #         raise HTTPException(status_code=status.HTTP_200_OK,
    #                             detail=f'No IPC with this device_id: {condition.device_id} found')
    #     api_port = settings.PORT
    #     response = logfiles_superuser_login(ipc.ip, api_port)
        
    #     if response['result'] != 'success' :
    #         raise HTTPException(status_code=response['status_code'],
    #                 detail=response['result'])
        
    #     header = {}
    #     header['Authorization'] = 'Bearer {}'.format(response['access_token'])
        
    #     #self.mcs_logger.debug('requests.post : {}'.format(data))
    #     try:
    #         url = 'http://{}:{}/api/log/files/list'.format(ipc.ip, api_port)
    #         payload = jsonable_encoder(condition)
    #         payload['device_id'] = ''
    #         res = requests.post(url, headers=header, json=payload, timeout=5)
    #     except requests.ConnectionError:
    #         glogger.error('requests.ConnectionError : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_get_log_file_list requests.ConnectionError : {}'.format(url))
    #     except requests.Timeout:
    #         glogger.error('requests.Timeout : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_get_log_file_list requests.Timeout : {}'.format(url))
    #     except:
    #         glogger.error(traceback.format_exc())
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_get_log_file_list exception : {}'.format(url))
            
    #     #self.mcs_logger.debug('requests.post : [{}] {}'.format(res.status_code, res.text))
    #     response = json.loads(res.text)
    #     response['status_code'] = res.status_code
    #     response['reason'] = res.reason
    #     #print(response)
        
    #     if res.status_code != 200:
    #         pass
    #     else:
    #         pass
        
    #     glogger.info('api_get_log_file_list : {} : {}'.format(condition.device_id, search), {'user': '{},{}'.format(login_user.userid,login_user.name)})
    #     return response
    res_search = filelist[condition.start:condition.start+condition.length]
        
    total = len(res_search)
    glogger.info('api_get_log_file_list : {} {}'.format(search, total), {'user': '{},{}'.format(login_user.userid,login_user.name)})
    return {'draw': condition.draw, 'recordsTotal': total, 'recordsFiltered': total, 'data': res_search}

@router.post('/files/view')
async def api_view_log_file(
        request: Request, 
        condition: schemas.LogFileNameSchema,
        api_response: Response,
        db: Session = Depends(get_db),
        login_id: str = Depends(oauth2.require_user),
    ):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_view_log_file : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    # device_id = condition.device_id.strip()
    # filepath = condition.filepath.strip()
    filename = condition.filename.strip()
    
    # bFilepath = False
    bFilename = False
    
    # if len(filepath) > 0 and isdir(filepath):
    #     bFilepath = True
    if len(filename) > 0:
        bFilename = True
    
    # if len(device_id) == 0 :
    if settings.LOG_DIRS:
        dirs = settings.LOG_DIRS.split(',')

        for dir in dirs:
            # if isdir(join(os.getenv('HOME'), d)):
            if isdir(dir):
                try:
                    for rootdir, subdirs, files in os.walk(dir):
                        # print('~~~~~~')
                        # for subdir in subdirs:
                        #     print('{} ****'.format(os.path.join(rootdir, subdir)))
                        # print('------')
                        for file in files:
                            # print(os.path.join(rootdir, file))
                            path = os.path.join(rootdir, file)
                            ext = os.path.splitext(ntpath.basename(path))[1].lower()
                            if ext == '.log' or ext == '.txt' or '.log' in file.lower() :
                                # print(path)
                                # if bFilepath:
                                #     if rootdir != filepath:
                                #         continue
                                if bFilename:
                                    if file != filename:
                                        continue
                                # print('filepath: {}, filename: {}, extension: {}, modified: {}, size: {}'.format(
                                #         str(path),
                                #         ntpath.basename(path),
                                #         os.path.splitext(ntpath.basename(path))[1],
                                #         os.stat(path).st_mtime * 1000,
                                #         os.stat(path).st_size
                                #     ))
                                glogger.info('api_view_log_file : {}'.format(filename), {'user': '{},{}'.format(login_user.userid,login_user.name)})
                                headers = {'Content-Disposition': f'inline; filename="{filename}"'}
                                return FileResponse(path, headers=headers, media_type="text/plain")
                except Exception as e:
                    #db.rollback()
                    glogger.error('api_view_log_file error : {}'.format(str(e)))
                    return str(e), 400
    # else :
    #     return
    #     ipc = db.query(IPC).filter(IPC.device_id == device_id).first()
        
    #     if not ipc:
    #         glogger.warning('api_view_log_file : No IPC with this device_id {} found.'.format(condition.device_id), 
    #                         {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #         raise HTTPException(status_code=status.HTTP_200_OK,
    #                             detail=f'No IPC with this device_id: {condition.device_id} found')
    #     api_port = settings.PORT
    #     response = logfiles_superuser_login(ipc.ip, api_port)
        
    #     if response['result'] != 'success' :
    #         raise HTTPException(status_code=response['status_code'],
    #                 detail=response['result'])
        
    #     header = {}
    #     header['Authorization'] = 'Bearer {}'.format(response['access_token'])
        
    #     #self.mcs_logger.debug('requests.post : {}'.format(data))
    #     try:
    #         url = 'http://{}:{}/api/log/files/view'.format(ipc.ip, api_port)
    #         payload = jsonable_encoder(condition)
    #         payload['device_id'] = ''
    #         res = requests.post(url, headers=header, json=payload, timeout=5)
    #     except requests.ConnectionError:
    #         glogger.error('api_view_log_file : requests.ConnectionError : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_view_log_file requests.ConnectionError : {}'.format(url))
    #     except requests.Timeout:
    #         glogger.error('api_view_log_file : requests.Timeout : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_view_log_file requests.Timeout : {}'.format(url))
    #     except:
    #         glogger.error(traceback.format_exc())
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_view_log_file exception : {}'.format(url))
            
    #     #self.mcs_logger.debug('requests.post : [{}] {}'.format(res.status_code, res.text))
    #     # response = json.loads(res.text)
    #     return Response(content=res.content, status_code=res.status_code, headers=res.headers, media_type="text/plain")
 
    return 'NOT FOUND', 404


@router.post('/files/download')
async def api_download_log_file(
        request: Request, 
        condition: schemas.LogFileNameSchema,
        api_response: Response,
        db: Session = Depends(get_db),
        login_id: str = Depends(oauth2.require_user),
    ):
    glogger = request.app.state.glogger
    
    login_user = db.query(User).filter(User.id == login_id).first()
    
    if login_user.acc_type == 'ALL' :
        glogger.warning('api_download_log_file : You are not allowed to perform this action.', 
                        {'user': '{},{}'.format(login_user.userid, login_user.name)})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not allowed to perform this action')
    
    # device_id = condition.device_id.strip()
    # filepath = condition.filepath.strip()
    filename = condition.filename.strip()
    
    # bFilepath = False
    bFilename = False
    
    # if len(filepath) > 0 and isdir(filepath):
    #     bFilepath = True
    if len(filename) > 0:
        bFilename = True
    
    # if len(device_id) == 0 :
    if settings.LOG_DIRS:
        dirs = settings.LOG_DIRS.split(',')

        for dir in dirs:
            # if isdir(join(os.getenv('HOME'), d)):
            if isdir(dir):
                try:
                    for rootdir, subdirs, files in os.walk(dir):
                        # print('~~~~~~')
                        # for subdir in subdirs:
                        #     print('{} ****'.format(os.path.join(rootdir, subdir)))
                        # print('------')
                        for file in files:
                            # print(os.path.join(rootdir, file))
                            path = os.path.join(rootdir, file)
                            ext = os.path.splitext(ntpath.basename(path))[1].lower()
                            if ext == '.log' or ext == '.txt' or '.log' in file.lower() :
                                # print(path)
                                # if bFilepath:
                                #     if rootdir != filepath:
                                #         continue
                                if bFilename:
                                    if file != filename:
                                        continue
                                # print('filepath: {}, filename: {}, extension: {}, modified: {}, size: {}'.format(
                                #         str(path),
                                #         ntpath.basename(path),
                                #         os.path.splitext(ntpath.basename(path))[1],
                                #         os.stat(path).st_mtime * 1000,
                                #         os.stat(path).st_size
                                #     ))
                                glogger.info('api_download_log_file : {}'.format(filename), {'user': '{},{}'.format(login_user.userid,login_user.name)})
                                # Create a temporary file to hold a snapshot of the log
                                if filename == 'api.log':
                                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                                        shutil.copyfile(path, temp_file.name)
                                        # Serve the static temporary file
                                        return FileResponse(path=temp_file.name, filename='api.log', background=BackgroundTask(lambda: os.remove(temp_file.name)))
                                else:
                                    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
                                    return FileResponse(path, headers=headers, media_type="text/plain")
                except Exception as e:
                    #db.rollback()
                    glogger.error('api_download_log_file error : {}'.format(str(e)))
                    return str(e), 400
    # else :
    #     return
    #     ipc = db.query(IPC).filter(IPC.device_id == device_id).first()
        
    #     if not ipc:
    #         glogger.warning('api_download_log_file : No IPC with this device_id {} found.'.format(condition.device_id), 
    #                         {'user': '{},{}'.format(login_user.userid, login_user.name)})
    #         raise HTTPException(status_code=status.HTTP_200_OK,
    #                             detail=f'No IPC with this device_id: {condition.device_id} found')
    #     api_port = settings.PORT
    #     response = logfiles_superuser_login(ipc.ip, api_port)
        
    #     if response['result'] != 'success' :
    #         raise HTTPException(status_code=response['status_code'],
    #                 detail=response['result'])
        
    #     header = {}
    #     header['Authorization'] = 'Bearer {}'.format(response['access_token'])
        
    #     #self.mcs_logger.debug('requests.post : {}'.format(data))
    #     try:
    #         url = 'http://{}:{}/api/log/files/download'.format(ipc.ip, api_port)
    #         payload = jsonable_encoder(condition)
    #         payload['device_id'] = ''
    #         res = requests.post(url, headers=header, json=payload, timeout=5)
    #     except requests.ConnectionError:
    #         glogger.error('api_download_log_file : requests.ConnectionError : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_download_log_file requests.ConnectionError : {}'.format(url))
    #     except requests.Timeout:
    #         glogger.error('api_download_log_file : requests.Timeout : {}'.format(url))
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_download_log_file requests.Timeout : {}'.format(url))
    #     except:
    #         glogger.error(traceback.format_exc())
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             detail='api_download_log_file exception : {}'.format(url))
            
    #     #self.mcs_logger.debug('requests.post : [{}] {}'.format(res.status_code, res.text))
    #     # response = json.loads(res.text)
    #     return Response(content=res.content, status_code=res.status_code, headers=res.headers, media_type="text/plain")
 
    return 'NOT FOUND', 404

# @router.post('/files/<start_datetime>/<end_datetime>')
# async def api_download_logs_between_datetime(start_datetime, end_datetime):

#     if 'LOG_DIRS' in app.config:
#         start_timestamp  = datetime.timestamp(datetime.strptime(start_datetime, '%Y-%m-%d'))
#         end_timestamp   = datetime.timestamp(datetime.strptime(end_datetime, '%Y-%m-%d') + timedelta(days=1))
#         # print(start_timestamp, end_timestamp)
#         filepaths = []
#         dirs = app.config.get('LOG_DIRS').split(',')
#         logFromMR = app.config.get('LOG_FROM_MR', False)
#         # print(dirs)
#         UIDir = os.path.abspath(dirs[0])
#         # print(UIDir)

#         for d in dirs:
#             d = os.path.abspath(d)
#             # print(d)
#             for root, dirs, files in os.walk(d):
#                 for file in files:
#                     filepath = os.path.join(root, file)                    
#                     modified_time = os.path.getmtime(filepath)
#                     if start_timestamp <= modified_time <= end_timestamp and '.zip' not in filepath:
#                         filepaths.append(filepath)

#         with zipfile.ZipFile('{}/{}-{}.zip'.format(UIDir, start_datetime, end_datetime), mode='w') as zf:
#             for filepath in filepaths:
#                 zf.write(filepath, basename(filepath))

#             if logFromMR:
#                 vehicles = Vehicle.query.filter(Vehicle.project == gv.get('projectName'), Vehicle.ip != "127.0.0.1").all()

#                 if vehicles is not None:
#                     startdate = start_datetime.replace("-", "")
#                     enddate = end_datetime.replace("-", "")
#                     for v in vehicles:
#                         ip = v.ip
#                         vehicleID = v.vehicleID
#                         payload = {
#                             "uuid": "1",
#                             "command": "loggather",
#                             "data":{
#                                 "startdate": startdate,
#                                 "enddate": enddate,
#                                 "keys": "test"
#                             }
#                         }
#                         # print(vehicleID, ip, payload)

#                         try:
#                             r = requests.post('http://{}:{}/getlogzipfile/'.format(ip, 8080), json=payload)
#                             # print(r.status_code)
#                             with zf.open('{}-VehicleLog.zip'.format(vehicleID), 'w') as f:
#                                 for chunk in r.iter_content(chunk_size=8388608):
#                                     f.write(chunk)
#                         except Exception as e:
#                             logger.error(traceback.format_exc())

#         return send_file(
#             '{}/{}-{}.zip'.format(UIDir, start_datetime, end_datetime),
#             as_attachment=True,
#             attachment_filename='{}/{}-{}.zip'.format(UIDir, start_datetime, end_datetime)
#         )

#     return 'NOT FOUND', 404
