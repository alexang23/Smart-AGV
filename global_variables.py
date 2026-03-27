# # import collections
# # import logging
# # import datetime
# from database import get_db
# from models.secs import SECS

# # handler_list = {}

# # event_queue = collections.deque()
# # alarm_queue = collections.deque()
# # eq_queue = collections.deque()
# # port_queue = collections.deque()
# # transfer_queue = collections.deque()

# ftp_alarmlist = {}
# db = next(get_db())
# messages = db.query(SECS).all()
# for msg in messages:
#     # print(msg)
#     if msg.sf not in ftp_alarmlist :
#         ftp_alarmlist[msg.sf] = {}
#     if msg.code not in ftp_alarmlist[msg.sf] :
#         ftp_alarmlist[msg.sf][msg.code] = {}
#     if msg.subcode not in ftp_alarmlist[msg.sf][msg.code] :
#         ftp_alarmlist[msg.sf][msg.code][msg.subcode] = {'msgtext':msg.msgtext, 'ftp':msg.ftp}

import csv
from config import settings

# Replace 'your_file.tsv' with the actual name of your file.
if settings.E84_TYPE == 0:
    file_path = 'e84_alarm_code_andrews.csv'
else:
    file_path = 'e84_alarm_code.csv'

alarm_code = {}
try:
    print(f"Read file {file_path}.")
    with open(file_path, mode='r', newline='') as file:
        # Use csv.reader with the tab delimiter
        reader = csv.reader(file, delimiter=',')
        
        # Read the header
        header = next(reader)
        # print(f"Header: {header}")
        
        n = 1
        # Loop through the rows and print them
        for row in reader:
            # print(f"{n},{row[0]}")
            alarm_code[int(row[0])] = [row[1], True if row[2] == '1' else False]
            n += 1
        # for key, value in alarm_code:
        #     print(f"{key},{value}")
        # print(alarm_code)
        # pass

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")


