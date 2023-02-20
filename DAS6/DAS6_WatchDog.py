# -*- coding: utf-8 -*-
from datetime import datetime,date
from os import path
from sendMailV1 import mailer as mail 
import json
from time import sleep

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

destinationEmailAddress = creds['destinationEmailAddress']

marketCloseHH = 15
marketCloseMM = 30

def printer(inText):
    print(f'{str(datetime.now())[:19]} {inText}')

def log(txt):
	directory = path.join('Logs',str(date.today())+'_DAS6Logs')
	if not path.exists(directory):
		path.makedirs(directory)
	logFile = path.join(directory,str(date.today())+'_DAS6_watchDogLogs.log')
	logMsg = '\n'+str(datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg) 
        
def lastTimeCheck(fileName): 
    logsDirectory = path.join('Logs',str(date.today())+'_DAS6Logs')    
    connFile = path.join(logsDirectory,str(date.today())+fileName)
    with open(connFile, 'r') as f:
        lines = f.readlines()
    loglastline = lines[-1].strip()
    # Parse the timestamp in loglastline into a datetime object
    timestamp_str = loglastline.split()[0] + ' ' + loglastline.split()[1]
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    # Get the current time as a datetime object
    now = datetime.now()    
    # Calculate the time difference
    time_diff = now - timestamp
    # Get the total number of seconds in the time difference
    seconds_diff = time_diff.total_seconds()    
    return seconds_diff


log('DAS6 WatchDog started')
printer('DAS6 WatchDog started')

while (datetime.now().replace(second=0, microsecond=0) < datetime.now().replace(hour=marketCloseHH, minute=marketCloseMM,second=0, microsecond=0)):
    nfoLastEntry = lastTimeCheck('_DAS6_NFO_FULL.log')
    bnfoLastEntry = lastTimeCheck('_DAS6_BNFO_FULL.log')
    
    log(f'Time since last entry in _DAS6_NFO_FULL.log : {nfoLastEntry} seconds')
    log(f'Time since last entry in _DAS6_BNFO_FULL.log : {bnfoLastEntry} seconds')
    
    #Check if it has been 6 minutes or more since the last conenction message in DAS6 logs
    if (nfoLastEntry>360) or (bnfoLastEntry>360) :
        msg = ''
        if nfoLastEntry>360:
            msg = msg + f'NFO stalled. It has been {round(nfoLastEntry/60)} minutes since the last connection message\n'
        if bnfoLastEntry>360:
            msg = msg + f'BNFO stalled. It has been {round(bnfoLastEntry/60)} minutes since the last connection message\n'   
        log(f"STALLED: {msg}")
        printer(f"STALLED: {msg}")
        mail(destinationEmailAddress,f"DAS6 WatchDog {date.today()}:  DAS6 STALLED",msg)
    else:
        msg = f'NFO and BNFO seem to be alive.\nTime since last entry in DAS6_NFO_FULL: {nfoLastEntry}.\nTime since last entry in DAS6_BNFO_FULL: {bnfoLastEntry}'
        log(msg)
        printer(msg)
    
    #Sleeping for 5 minutes
    sleep(300)

log('DAS6 WatchDog - Done for the day')
printer('DAS6 WatchDog - Done for the day')
