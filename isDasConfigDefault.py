"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
"""

import json
from DAS_errorLogger import DAS_errorLogger
from os import path, makedirs 
from datetime import datetime as dt, date

def dasconfigDefaultsCheckLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'dasConfig.json - DAS_isConfigDefaultLogs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

def isDasConfigDefault():
    dasDefaults = False
    configFile = 'dasConfig.json'
    with open(configFile,'r') as configFile:
        dasConfig = json.load(configFile)

    destinationEmailAddress = dasConfig['destinationEmailAddress']
    senderEmailAddress = dasConfig['senderEmailAddress']
    senderEmailPass = dasConfig['senderEmailPass']
    TOTP_seed = dasConfig['TOTP_seed']
    zerodhaLoginName = dasConfig['ZerodhaLoginName']
    zerodhaPass = dasConfig['ZerodhaPass']
    apiKey = dasConfig['apiKey']
    apisec = dasConfig['apisec']
    mysqlHost = dasConfig['mysqlHost']
    mysqlUser = dasConfig['mysqlUser']
    mysqlPass = dasConfig['mysqlPass']
    
    if destinationEmailAddress == "Your_destinationEmailAddress1,Your_destinationEmailAddress2":
        msg = f'dasConfig.json - destinationEmailAddress has default value {destinationEmailAddress}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True
    if senderEmailAddress == "Your_SenderEmailAddressATgmail.com":
        msg = f'dasConfig.json - senderEmailAddress has default value {senderEmailAddress}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True 
    if senderEmailPass == "Your_SenderEmailPass":
        msg = f'dasConfig.json - senderEmailPass has default value {senderEmailPass}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True       
    if TOTP_seed == "Your_TOTP_seed":
        msg = f'dasConfig.json - TOTP_seed has default value {TOTP_seed}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True  
    if zerodhaLoginName == "Your_ZerodhaLoginName":
        msg = f'dasConfig.json - zerodhaLoginName has default value {zerodhaLoginName}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True   
    if zerodhaPass == "Your_ZerodhaPass":
        msg = f'dasConfig.json - zerodhaPass has default value {zerodhaPass}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True    
    if apiKey == "Your_Zerodha_apiKey":
        msg = f'dasConfig.json - apiKey has default value {apiKey}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True  
    if apisec == "Your_Zerodha_apisec":
        msg = f'dasConfig.json - apisec has default value {apisec}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True 
    if mysqlHost == "Your_mysqlHost":
        msg = f'dasConfig.json - mysqlHost has default value {mysqlHost}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True 
    if mysqlUser == "Your_mysqlUser":
        msg = f'dasConfig.json - mysqlUser has default value {mysqlUser}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True  
    if mysqlPass == "Your_mysqlPass":
        msg = f'dasConfig.json - mysqlPass has default value {mysqlPass}'
        dasconfigDefaultsCheckLogger(msg)
        DAS_errorLogger(msg)
        dasDefaults = True         
    return dasDefaults
    
if __name__ == '__main__':
    isDasConfigDefault()
    

