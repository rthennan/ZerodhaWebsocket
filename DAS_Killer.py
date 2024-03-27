"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

This is just a countdown timer that runs in parallel with the ticker.
When this script is over, the actual ticker is killed and backup operations are called
"""
from datetime import datetime as dt, date
import time
from os import path, makedirs
from DAS_errorLogger import DAS_errorLogger
import sys

def killerLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_Killer_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)

def remain(h,m):
    stopTime = (dt.now()).replace(hour=h, minute=m, second=0, microsecond=0)
    return int((stopTime - dt.now()).total_seconds())
        
def killer(h,m):
    timeUp = False
    msg = f'DAS Killer - Called with endTime - {h}:{m}'
    killerLogger(msg)
    stopTime = (dt.now()).replace(hour=h, minute=m, second=0, microsecond=0)
    if stopTime <= dt.now():
        msg = 'DAS Killer - End time provided is in the past. Exiting'
        killerLogger(msg)
        DAS_errorLogger(msg)
        sys.exit()
    else:
        delay = int((stopTime - dt.now()).total_seconds())
        msg = f'DAS Killer - Sleep Time estimated - {round(delay/60)} minutes. '
        killerLogger(msg)
        msg = 'DAS Killer - Entering hibernation'
        killerLogger(msg)
        time.sleep(delay+1)
        while not timeUp:
            #If killer wokeup earlier somehow
            if dt.now() >= stopTime:
                timeUp = True
                msg = 'DAS Killer - Time Up. Exiting'
                killerLogger(msg)
            else:
                msg = 'DAS Killer - Still running. Sleeping for 30 seconds'
                killerLogger(msg)
                time.sleep(30)
                