"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan

kiteConnect ticker field name changes in v4 and later.
https://github.com/zerodha/pykiteconnect?tab=readme-ov-file#v4---breaking-changes

Incorporated already and tested in KiteConnect Version : 5.0.1
The DB Tables would still hold the old names.So this is just for reference.
Old Name => New Name:
    timestamp => exchange_timestamp
    last_quantity => last_traded_quantity
    average_price => average_traded_price
    volume => volume_traded
    buy_quantity => total_buy_quantity
    sell_quantity => total_sell_quantity
"""

import pandas as pd
import numpy as np
from datetime import datetime as dt, date
import MySQLdb
from kiteconnect import KiteTicker
import traceback
import json
from os import path, makedirs
from DAS_gmailer import DAS_mailer
from DAS_errorLogger import DAS_errorLogger

configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)
apiKey = dasConfig['apiKey']
mysqlHost = dasConfig['mysqlHost']
mysqlUser = dasConfig['mysqlUser']
mysqlPass = dasConfig['mysqlPass']
mysqlPort = dasConfig['mysqlPort']

accessTokenDBName = dasConfig['accessTokenDBName']
zerodhaLoginName = dasConfig['ZerodhaLoginName'] 
nifty500_daily_DBName = dasConfig['nifty500DBName']+'_daily'
niftyOptions_daily_DBName = dasConfig['niftyOptionsDBName']+'_daily'
bankNiftyOptions_daily_DBName = dasConfig['bankNiftyOptionsDBName']+'_daily'

conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
conn.autocommit(True)
c = conn.cursor()

def DAS_Tickerlogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_Ticker_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)

def DAS_Ticker():
    lookupDir = 'lookupTables'
    
    #Identify Only Nifty and BankNifty as they have a different table structure and hence different SQL stmnt
    indexTokens = pd.read_csv(path.join(lookupDir,'indexTokenList.csv'))['instrument_token'].values.tolist()  
   
    #Nifty500 Tokens and Token Table (Lookup => instrument_token:TableName)
    #Includes Nifty 500, Nifty, BankNifty and their Futures
    nifty500Tokens = pd.read_csv(path.join(lookupDir,'nifty500TokenList.csv'))['instrument_token'].values.tolist()
    nifty500TokenTable = np.load(path.join(lookupDir,'nifty500TokenTable.npy'),allow_pickle=True).item() 
    
    #Nifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
    niftyOptionTokens = pd.read_csv(path.join(lookupDir,'niftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
    niftyOptionsTokenTable = np.load(path.join(lookupDir,'niftyOptionsTokenTable.npy'),allow_pickle=True).item() 
    
    #BankNifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
    bankNiftyOptionTokens = pd.read_csv(path.join(lookupDir,'bankNiftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
    bankNiftyOptionsTokenTable = np.load(path.join(lookupDir,'bankNiftyOptionsTokenTable.npy'),allow_pickle=True).item() 
    
    #Combining all three token lists. Subscribing to this master list
    fullTokenList = nifty500Tokens + niftyOptionTokens + bankNiftyOptionTokens
    
    #Combine all three dictionairies
    masterTokenTable = {}
    masterTokenTable.update(nifty500TokenTable)
    masterTokenTable.update(niftyOptionsTokenTable)
    masterTokenTable.update(bankNiftyOptionsTokenTable)

    #Creating a lookup dictionairy for instrument_token:DBName
    tokenToDbName = {token: nifty500_daily_DBName for token in nifty500Tokens}
    tokenToDbName.update({token: niftyOptions_daily_DBName for token in niftyOptionTokens})
    tokenToDbName.update({token: bankNiftyOptions_daily_DBName for token in bankNiftyOptionTokens})

    def replace(ticker):
        global c
        global conn
        #Perform DB Operations
        if 'instrument_token' in ticker:
            #If Instrument Token Belongs to NIFTY or BANKNIFTY Index
            if ticker['instrument_token'] in indexTokens:
                try:
                    c.execute(f"REPLACE INTO {nifty500_daily_DBName}.`{masterTokenTable[ticker['instrument_token']]}` VALUES (%s,%s)",[ticker['exchange_timestamp'],ticker['last_price']])
                except Exception as e:
                    msg = f'{str(ticker)} Could not be inserted to DB. Exception: {str(e)}. Traceback: {traceback.format_exc()}'
                    DAS_Tickerlogger(msg)
                    c.close()
                    conn.close()
                    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
                    conn.autocommit(True)
                    c = conn.cursor()
            else:
                
                try:
                    #DBName fetched from tokenToDbName
                    c.execute(f"REPLACE INTO {tokenToDbName[ticker['instrument_token']]}.`{masterTokenTable[ticker['instrument_token']]}` VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
                                                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
                                                       %s,%s,%s,%s,%s,%s)",[ticker['exchange_timestamp'],ticker['last_price'],\
                    ticker['last_traded_quantity'],ticker['average_traded_price'],ticker['volume_traded'],ticker['total_buy_quantity'],\
                    ticker['total_sell_quantity'],ticker['ohlc']['open'],ticker['ohlc']['high'],ticker['ohlc']['low'], ticker['ohlc']['close'],\
                    ticker['change'], ticker['last_trade_time'],ticker['oi'],ticker[ 'oi_day_high'], ticker['oi_day_low'],\
                    ticker['depth']['buy'][0]['quantity'], ticker['depth']['buy'][0]['price'],ticker['depth']['buy'][0]['orders'],\
                    ticker['depth']['buy'][1]['quantity'], ticker['depth']['buy'][1]['price'],ticker['depth']['buy'][1]['orders'],\
                    ticker['depth']['buy'][2]['quantity'], ticker['depth']['buy'][2]['price'],ticker['depth']['buy'][2]['orders'],\
                    ticker['depth']['buy'][3]['quantity'], ticker['depth']['buy'][3]['price'],ticker['depth']['buy'][3]['orders'],\
                    ticker['depth']['buy'][4]['quantity'], ticker['depth']['buy'][4]['price'],ticker['depth']['buy'][4]['orders'],\
                    ticker['depth']['sell'][0]['quantity'], ticker['depth']['sell'][0]['price'],ticker['depth']['sell'][0]['orders'],\
                    ticker['depth']['sell'][1]['quantity'], ticker['depth']['sell'][1]['price'],ticker['depth']['sell'][1]['orders'],\
                    ticker['depth']['sell'][2]['quantity'], ticker['depth']['sell'][2]['price'],ticker['depth']['sell'][2]['orders'],\
                    ticker['depth']['sell'][3]['quantity'], ticker['depth']['sell'][3]['price'],ticker['depth']['sell'][3]['orders'],\
                    ticker['depth']['sell'][4]['quantity'], ticker['depth']['sell'][4]['price'],ticker['depth']['sell'][4]['orders']])
                except Exception as e:
                    msg = f' {str(ticker)} Could not be inserted to DB. Exception: {str(e)}. Traceback : {traceback.format_exc()}'
                    DAS_Tickerlogger(msg)
                    c.close()
                    conn.close()
                    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
                    conn.autocommit(True)
                    c = conn.cursor()                    
        else:
            #Log Error
            msg = f'{str(ticker)} Could not be inserted to DB. Token not found'
            DAS_Tickerlogger(msg)  
            DAS_errorLogger('DAS_Ticker - '+msg)
    try:
        #Get latest access token from DB
        conne = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, db=accessTokenDBName, port=mysqlPort)
        ce = conne.cursor()
        ce.execute('select accessToken from kite1tokens order by timestamp desc limit 1')
        acc_token = str(ce.fetchone()[0])
        ce.close()
        conne.close()    
     
        kws = KiteTicker(apiKey, acc_token)
        
        def on_ticks(ws, ticks):
            for tickers in ticks:
                #print(tokenSymbol.get(tickers.get('instrument_token')),"  ", tickers.get('last_trade_time'))
                #print(tickers)
                # for tick in response:
                #    print(type(tick))
                replace(tickers)
        
            
        def on_connect(ws, response):
            msg = "DAS Ticker : Connection Successful"
            DAS_Tickerlogger(msg)
            ws.subscribe(fullTokenList)
            ws.set_mode(ws.MODE_FULL, fullTokenList)
            
        def on_close(ws, code, reason):
            # On connection close stop the main loop
            # Reconnection will not happen after executing `ws.stop()`
            ws.stop()
            
        # Assign the callbacks.
        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.connect()
        
    except Exception as e:
        msg = f'DAS Ticker - Dump Failed. Exception : {e}. Traceback :  {str(traceback.format_exc())}'  
        DAS_Tickerlogger(msg)
        DAS_errorLogger('DAS_Ticker - '+msg)
        DAS_mailer('DAS Ticker - Dump Failed.',msg)