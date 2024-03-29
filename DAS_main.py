# -*- coding: utf-8 -*-
"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
"""


from os import path, makedirs
import sys
import multiprocessing
from datetime import datetime as dt, date

from tradeHolidayCheck import tradeHolidayCheck
from accessTokenReq import accessTokenReq
from nifty500Updater import nifty500Updater
from lookupTablesCreator import lookupTablesCreator
from DAS_Ticker import DAS_Ticker
from DAS_Killer import killer
import traceback
from DAS_dailyBackup import DAS_dailyBackup
from DAS_gmailer import DAS_mailer
from DAS_errorLogger import DAS_errorLogger
import json
from isDasConfigDefault import isDasConfigDefault

configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)

marketCloseHour = dasConfig['marketCloseHour']
marketCloseMinute = dasConfig['marketCloseMinute']


def dasMainlogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_main_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)

if __name__ == '__main__':
    try:
        #Some checkes can be combined into fewer lines with one statement or nested ifs.
        #Doing it this way for better readability
        #Will return True if Holiday
        
        isTradingHoliday = tradeHolidayCheck(str(date.today())) 
        
        if isTradingHoliday: 
            msg = f'DAS Main - Today {date.today()} is a trading Holiday. DAS Main exiting'
            dasMainlogger(msg)
            DAS_mailer("DAS Main - Trading Holiday. Exiting !!!",msg)
            DAS_errorLogger(msg)
            sys.exit()
        else: 
            msg = 'DAS Main - Trading Holiday Check Passed. Proceeding to dasConfig default check'
            dasMainlogger(msg)
            dasConfigIsDefault = isDasConfigDefault()
            
        if dasConfigIsDefault: 
            msg = 'DAS Main - dasConfig.json has invalid default values. DAS Main exiting'
            dasMainlogger(msg)
            DAS_errorLogger(msg)
            sys.exit()
        else: 
            msg = 'dasConfigIsDefault Check Passed. Proceeding to accessTokenReq'
            dasMainlogger(msg)
            accessTokenSuccess = accessTokenReq()            
        #Are credentials valid?
        if not accessTokenSuccess: 
            msg = 'DAS Main - accessTokenReq Failed. DAS Main exiting.\naccessTokenReq.py failed'
            dasMainlogger(msg)
            DAS_mailer("DAS Main - accessTokenReq Failed. Exiting !!!",msg)
            DAS_errorLogger(msg)
            sys.exit()
        else:
            msg = 'DAS Main - accessToken fetched Successfully. Proceeding to nifty500Updater'
            dasMainlogger(msg)
            nifty500updateSuccess = nifty500Updater()
        
        #Was nifty500Updater() successfull?
        if not nifty500updateSuccess :
            msg = 'DAS Main - nifty500Updater FAILED!!!. DAS Main exiting'
            dasMainlogger(msg)
            DAS_errorLogger(msg)
            DAS_mailer("DAS Main - nifty500Updater Failed. Exiting !!!",msg)
            sys.exit()
        else:
            msg = 'DAS Main - nifty500Updater succeeded. Proceeding to lookupTablesCreator'
            dasMainlogger(msg)
            lookupTableCreationSuccess = lookupTablesCreator()
        #Was lookupIns_NSE() successfull?
        if not lookupTableCreationSuccess :
            msg = 'DAS Main - lookupTablesCreator FAILED!!!. DAS Main exiting'
            dasMainlogger(msg)
            DAS_errorLogger(msg)
            DAS_mailer("DAS Main - lookupTablesCreator Failed. Exiting !!!",msg)
            sys.exit()    
        #An else would do here. But doing elif just in case and why not?
        elif (not isTradingHoliday) and accessTokenSuccess and nifty500updateSuccess and lookupTableCreationSuccess:
            msg = f'lookupTablesCreator succeeded. All Pre-checks passed. Proceeding wtih DAS ticker at {str(dt.now())[:19]}'
            dasMainlogger(msg)
            
            DAS_ticker_process = multiprocessing.Process(target=DAS_Ticker)
            DAS_ticker_process.start()
            msg = f'All Preparation steps and rpechecks completed successfully. Proceeding wtih DAS ticker.\nTicker will be closed at {dt.now().replace(hour=marketCloseHour, minute=marketCloseMinute, second=0, microsecond=0)}'
            DAS_mailer(f'DAS Main - Ticker Started at {str(dt.now())[:19]}',msg)
            #DAS_ticker_process is started as a parallel thread.
            #killer is a countdown timer that runs in parallel with the ticker.
            #When this script is over, the actual ticker is killed and backup operations are called
            killer(marketCloseHour,marketCloseMinute)
            ### Killing Ticker ###        
            try:
                DAS_ticker_process.terminate()
                tickerClosed =True
            except Exception as e:
                msg = f"DAS Main - Exception: DAS_ticker_process couldn't be stopped. Exception : {e}.\Traceback :{str(traceback.format_exc())}"
                DAS_mailer('DAS ticker could not be stopped',msg)
                dasMainlogger(msg)
                DAS_errorLogger(msg)
            if not tickerClosed:
                msg = "DAS Main - DAS_ticker_process couldn't be stopped. Exiting execution. Check logs for more details"
                DAS_mailer('DAS ticker could not be stopped',msg)
                DAS_errorLogger(msg)
                dasMainlogger(msg)
            elif tickerClosed:
                msg = 'Ticker stopped Successfully. Proceeding to Backup'
                dasMainlogger(msg)
                #You are here
                backupStatus = DAS_dailyBackup()
                if backupStatus:
                    msg="DAS - All Activities for the day have been completed."
                    dasMainlogger(msg)
                else:
                    msg="DAS Main - DAS_dailyBackup reported failure. Check logs thoroughly."
                    dasMainlogger(msg)
                    DAS_errorLogger(msg)
    except Exception as e:
        msg = f'DAS Main Failed. Exception : {e}. Traceback :  {str(traceback.format_exc())}'  
        dasMainlogger(msg)
        DAS_errorLogger(msg)
        DAS_mailer('DAS Main Failed.',msg)