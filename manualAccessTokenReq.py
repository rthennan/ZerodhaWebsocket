"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Generate Access Token manually , as a failover for accessToneReq
Toubleshooting and fixing accesstokenReq before market opens is not always feasible

Steps:
    - Open serverd URL - Manual 
    - Generate Token/URL - Manual 
    - Paste response - Manual 
Extracts Tokens from the provided URL and stores it in {accessTokenDBName}.kite1tokens

"""
from kiteconnect import KiteConnect
from datetime import datetime as dt
from datetime import date
from os import path,makedirs
import json
from DAS_errorLogger import DAS_errorLogger
import traceback
import MySQLdb #sudo apt-get install python3-mysqldb

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

configFile = 'dasConfig_cust.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)

apiKey = dasConfig['apiKey']
apisec = dasConfig['apisec']
mysqlHost = dasConfig['mysqlHost']
mysqlUser = dasConfig['mysqlUser']
mysqlPass = dasConfig['mysqlPass']
mysqlPort = dasConfig['mysqlPort']
accessTokenDBName = dasConfig['accessTokenDBName']

def manualAccessTokenLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'manualAccessToken_Logs_{str(date.today())}.log')
    #Remove colour codes before logging
    colourCodes = [RED, GREEN, BLUE, YELLOW, CYAN, RESET]
    for colourCode in colourCodes:
        txt = txt.replace(colourCode, '')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

def manualAccessTokenReq():
    try:    
    
        kite = KiteConnect(api_key = apiKey)
        
        loginUrl = (kite.login_url())
        msg = f'{YELLOW}\n\nLogin to Kite manually with the below URL{RESET}\n\n{GREEN}{loginUrl}{RESET}'   
        manualAccessTokenLogger(msg)
        
        print('\n')
        #Enter the response URL 
        msg = f'{YELLOW}After successful login, copy the response URL from your browser and paste it below\n\n{RESET}'   
        manualAccessTokenLogger(msg)
        
        tokenUrl = input()
        
        print('\n')
        
        '''New Token fetch code'''
        lenReq = len("request_token=")
        reqToken = tokenUrl[tokenUrl.find('request_token=')+lenReq:]
        endChar = reqToken.find('&')
        if endChar!=-1:
            reqToken = reqToken[:endChar]
        #Token fetch code end
        msg = f'{YELLOW}Response URL: {GREEN}{tokenUrl}{RESET}\n'
        manualAccessTokenLogger(msg)
        msg = f'{YELLOW}Request Token: {GREEN}{reqToken}{RESET}'
        manualAccessTokenLogger(msg)
        manualAccessTokenLogger('Retrieving Access Token')
        session = kite.generate_session(reqToken, apisec)
        accessToken = session['access_token']
        msg = f'{YELLOW}Access Token: {GREEN}{accessToken}{RESET}'
        manualAccessTokenLogger(msg)
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
        conn.autocommit(True)
        c = conn.cursor()
        c.execute(f"CREATE DATABASE IF NOT EXISTS {accessTokenDBName}")
        #Why kite1tokens ? If zerodha imposes limits on the number of subscribable instruments in the fture, might need more API apps
        c.execute(f"CREATE TABLE IF NOT EXISTS {accessTokenDBName}.kite1tokens (timestamp DATETIME UNIQUE,requestUrl varchar(255) ,reqToken varchar(255) ,accessToken varchar(255))")
        shortsql = f"INSERT into {accessTokenDBName}.kite1tokens values (%s, %s, %s, %s)"
 
        c.execute(shortsql,[dt.now(),tokenUrl,reqToken,accessToken])
        manualAccessTokenLogger(f'{GREEN}Updated in DB{RESET}')
        msg = f'{GREEN}Manual Access Token success{RESET}'
        manualAccessTokenLogger(msg)
        
    except Exception as e:
        msg = f'Exception in manualAccessTokenReq -> {e}. Traceback : {traceback.format_exc()}'
        manualAccessTokenLogger(msg)
        DAS_errorLogger('manualAccessTokenReq Failed - '+msg)
    finally:
        c.close()
        conn.close()
        
if __name__ == '__main__':
    manualAccessTokenReq()