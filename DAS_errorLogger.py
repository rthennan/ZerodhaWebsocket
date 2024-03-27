# -*- coding: utf-8 -*-
"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan

All functions log their status and failures in their respective log files
But DAS_errorLogger is called on all failures, logging any failure from any function in DAS_Errors_yyyy-mm-dd.log
It also prints the error in Red (I hope)
"""

from datetime import datetime as dt, date
from os import path, makedirs

RED = '\033[91m'
RESET = '\033[0m'

def DAS_errorLogger(txt):
    print(f'{RED}{dt.now()} {txt}{RESET}')
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_Errors_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)