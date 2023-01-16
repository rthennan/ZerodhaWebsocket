# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:19:32 2019
Updated on 14 Mar 2020
- Combined NSE and Index Dumps
Modified on Mon Sep 21 03:02:23 2020
For AWS (Ubuntu)
@author: Thennan

uses Apikey2
"""

import pandas as pd
import numpy as np
import datetime
import MySQLdb
from sendMailV1 import mailer as mail
from kiteconnect import KiteTicker
import traceback
import json
from os import path, makedirs

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
apiKey2 = creds['apiKey2']
destinationEmailAddress = creds['destinationEmailAddress']

conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
conn.autocommit(True)
c = conn.cursor()

def DAS5_3_Ticker():    
    nseTokenList = pd.read_csv(path.join('lookup_tables','nseTokenList3.csv'))['instrument_token'].values.tolist()
    nseTokenTable = np.load(path.join('lookup_tables','nseTokenTable3.npy'),allow_pickle=True).item() 
    tokenList = nseTokenList
    
    
    def log(txt):
    	directory = path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
    	if not path.exists(directory):
    		makedirs(directory)
    	logFile = path.join(directory,str(datetime.date.today())+'_DAS5_3_Ticker.log')
    	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
    	with open(logFile,'a') as f:
    		f.write(logMsg)      
  
       
    def replace(ticker):
        global c
        global conn
        if 'instrument_token' in ticker:
            #Perform DB OPerations
                    
            try:
                c.execute("REPLACE INTO aws_das4daily.`"+nseTokenTable[ticker['instrument_token']]+"` VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
                                                   %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
                                                   %s,%s,%s,%s,%s,%s)",[ticker['timestamp'],ticker['last_price'],\
                ticker['last_quantity'],ticker['average_price'],ticker['volume'],ticker['buy_quantity'],\
                ticker['sell_quantity'],ticker['ohlc']['open'],ticker['ohlc']['high'],ticker['ohlc']['low'], ticker['ohlc']['close'],\
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
                msg = str(traceback.format_exc())
                print(str(datetime.datetime.now())+'    '+str(ticker))
                log(str(ticker)+' Could not be inserted to DB. Exception: '+str(e))
                log(msg)
                c.close()
                conn.close()
                conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
                conn.autocommit(True)
                c = conn.cursor()                    
        else:
            #Log Error
            print(str(datetime.datetime.now())+'    '+str(ticker))
            log(str(ticker)+' Could not be inserted to DB. Token not found')   
    try:
        conne = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, db='aws_tokens')
        conne.autocommit(True)
        ce = conne.cursor()
        ce.execute('select accessToken from das6 order by time desc limit 1')
        acc_token = str(ce.fetchone()[0])
        ce.close()
        conne.close()    
     
        kws = KiteTicker(apiKey2, acc_token)
        
        def on_ticks(ws, ticks):
            for tickers in ticks:
                #print(tokenSymbol.get(tickers.get('instrument_token')),"  ", tickers.get('last_trade_time'))
                #print(tickers)
                # for tick in response:
                #    print(type(tick))
                replace(tickers)
        
            
        def on_connect(ws, response):
            log("Connection Successful")
            print("Connected Successfully at "+str(datetime.datetime.now()))
            ws.subscribe(nseTokenList)
            ws.set_mode(ws.MODE_FULL, tokenList)
            
        def on_close(ws, code, reason):
            # On connection close stop the main loop
            # Reconnection will not happen after executing `ws.stop()`
            ws.stop()
            
        # Assign the callbacks.
        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.connect()
        
    except Exception as e:
        msg = "DAS5_3 - Dump Failed. Exception : "   + str(e)   
        log(msg)
        mail(destinationEmailAddress,'DAS5 - Dump 3 Failed',msg)
        print("DAS5 - Dump 3  Failed. Exception : "+str(e))
