import datetime
import pandas as pd
import numpy as np
import MySQLdb
from datetime import datetime as dt
import time
import multiprocessing
from kiteconnect import KiteConnect
import traceback
from DAS6_BNFO_Full_V1 import BNFO_FULL #Moded for Linux
from sendMailV1 import mailer as mail #Moded for Linux
from os import path, makedirs
from getExpiryPrefix import getExpPref
from dateutil.relativedelta import relativedelta
import json

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
apiKey1 = creds['apiKey1']
destinationEmailAddress = creds['destinationEmailAddress']

def log(txt):
	directory = path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
	if not path.exists(directory):
		makedirs(directory)
	logFile = path.join(directory,str(datetime.date.today())+'_BNFO_LookupLog.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg)
 

def dbCreate():
    conne = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
    conne.autocommit(True)
    c2 = conne.cursor()
    c2.execute("CREATE DATABASE IF NOT EXISTS aws_das2optionsdaily")
    c2.close()
    conne.close()

def BNFOlookup():
    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
    conn.autocommit(True)
    c = conn.cursor()
    numbOfRetries = 30
    for attempt in range(numbOfRetries):
        try:    
            #simmonsLookup = pd.read_csv(path.join('lookup_tables','bnfo_simmonsLookup.csv'))
            #tablePrefix = simmonsLookup.loc[simmonsLookup['date'] == pd.Timestamp("today").strftime("%Y-%m-%d")]['tablePrefix'].iloc[0]
            #currExpiry = simmonsLookup.loc[simmonsLookup['date'] == pd.Timestamp("today").strftime("%Y-%m-%d")]['currExpiry'].iloc[0]
            #nextExpiry = simmonsLookup.loc[simmonsLookup['date'] == pd.Timestamp("today").strftime("%Y-%m-%d")]['nextExpiry'].iloc[0]
            #Generating the expiry prefixes on the fly now.
            currExpiry = getExpPref('BANKNIFTY',dt.today().date())
            #Add 1 week to the current date and find its expiry, to get the next expiry  
            nextExpiry = getExpPref('BANKNIFTY',dt.today().date()+ relativedelta(weeks=1)) 
            
            """Using DAS5 App"""
            kite = KiteConnect(api_key=apiKey1)
    		
            c.execute('select accessToken from aws_tokens.das5 order by time desc limit 1')
            accessToken = str(c.fetchone()[0])
            kite.set_access_token(accessToken)
            
            bNiftyLTP = float(kite.ltp('NSE:NIFTY BANK')['NSE:NIFTY BANK']['last_price'])
            bNiftyLTP = round(float(bNiftyLTP)/100)*100
            
            SPs = []
            currExp = []
            nextExp = []            
            BNfos = []
            
            for x in range(bNiftyLTP-2500,bNiftyLTP+2500,100):
                SPs.append(x)
            for strikes in SPs:
                currExp.append(currExpiry+str(strikes))
                nextExp.append(nextExpiry+str(strikes))
                
            SPs = currExp+nextExp
            optSuffs = ['PE','CE']
            for x in optSuffs:
                for y in SPs:
                    BNfos.append(str(y)+str(x)) 
            msg = "BNiftyLTP ==> "+str(bNiftyLTP)+". Tables Finalized for BNfo for today ==> "+str(BNfos)    
            log(msg)                       
            tslice = str(datetime.date.today())
            fname = path.join('lookup_tables','instruments_'+tslice+'.csv')
            inst = pd.read_csv(fname,usecols=['instrument_token','tradingsymbol','exchange'])
            inst = inst[inst['exchange'].isin(['NSE','NFO'])]        
            bnfoInst = inst[inst['tradingsymbol'].isin(BNfos)].drop('exchange',axis=1)
            bnfoInst = bnfoInst.drop_duplicates()  
            bnfoTokenSymbol = bnfoInst.set_index('instrument_token')['tradingsymbol'].to_dict()     
    
            np.save(path.join('lookup_tables','bnfoTokenSymbol.npy'), bnfoTokenSymbol)
            #Instrumnet_Token_List 
            bnfoInst.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','bnfoTokenList.csv'),index=False)
            bnfoInst.to_csv(path.join('lookup_tables','bnfoTables.csv'),index=False)
    
            for tb in BNfos:
                c.execute("CREATE TABLE IF NOT EXISTS aws_das2optionsdaily.`"+tb+"` \
            	(timestamp DATETIME UNIQUE,price DECIMAL(19,2), qty INT UNSIGNED, avgPrice DECIMAL(19,2), volume BIGINT,\
                bQty INT UNSIGNED, sQty INT UNSIGNED, open DECIMAL(19,2), high DECIMAL(19,2), low DECIMAL(19,2), close DECIMAL(19,2),\
            	changeper DECIMAL(60,10), lastTradeTime DATETIME, oi INT, oiHigh INT, oiLow INT, \
            	bq0 INT UNSIGNED, bp0 DECIMAL(19,2), bo0 INT UNSIGNED,\
            	bq1 INT UNSIGNED, bp1 DECIMAL(19,2), bo1 INT UNSIGNED,\
            	bq2 INT UNSIGNED, bp2 DECIMAL(19,2), bo2 INT UNSIGNED,\
            	bq3 INT UNSIGNED, bp3 DECIMAL(19,2), bo3 INT UNSIGNED,\
            	bq4 INT UNSIGNED, bp4 DECIMAL(19,2), bo4 INT UNSIGNED,\
            	sq0 INT UNSIGNED, sp0 DECIMAL(19,2), so0 INT UNSIGNED,\
            	sq1 INT UNSIGNED, sp1 DECIMAL(19,2), so1 INT UNSIGNED,\
            	sq2 INT UNSIGNED, sp2 DECIMAL(19,2), so2 INT UNSIGNED,\
            	sq3 INT UNSIGNED, sp3 DECIMAL(19,2), so3 INT UNSIGNED, \
            	sq4 INT UNSIGNED, sp4 DECIMAL(19,2), so4 INT UNSIGNED)")
                
            c.close()
            conn.close()
            msg = 'NFO Look up successful.'
            log(msg)
            print(msg)
        except Exception as e:
            msg = str(traceback.format_exc())
            log('Instrument Lookup Failed. Attempt No. '+str(attempt)+' Exception-> '+str(e))
            log(msg)
            c.close()
            conn.close()
            conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
            conn.autocommit(True)
            c = conn.cursor()
            time.sleep(1)
        else:
            break
    else:
        msg = 'Instrument Lookup Failed After '+str(numbOfRetries)+' attempts. Will use Older lookup file'
        log(msg)
        c.close()
        conn.close()
        mail(destinationEmailAddress, 'DAS6: BNFO Instrument Token Lookup Failed.',msg)         
# =============================================================================
# 
# def remain(h,m):
#     stopTime = (dt.now()).replace(hour=h, minute=m, second=0, microsecond=0)
#     return int((stopTime - dt.now()).total_seconds())
# =============================================================================
   
def BNFO(marketCloseHH,marketCloseMM):
    marketCloseMM = marketCloseMM-1
    msg = "starting NFO Lookup"
    log(msg)
    dbCreate()
    while (dt.now().replace(second=0, microsecond=0) < dt.now().replace(hour=marketCloseHH, minute=marketCloseMM,second=0, microsecond=0)):
        BNFOlookup()
        msg = "Lookup done. starting data acquistion now."
        print(msg)
        log(msg)
        das6BNFOFULL = multiprocessing.Process(target=BNFO_FULL)
        das6BNFOFULL.start()
        delta = datetime.timedelta(seconds=30)
        #delta10min = datetime.timedelta(seconds=600)
        remainTime =(((dt.now().replace(hour=marketCloseHH, minute=marketCloseMM,second=0, microsecond=0)) - (dt.now().replace(second=0, microsecond=0)))+delta).total_seconds()
        if (remainTime >=300):
            delay = 300
        else:
            delay=remainTime
        log("Delay =>"+str(delay))
        print(dt.now(),msg)               
        time.sleep(delay)
        das6BNFOFULL.terminate() 
        msg = "5 minutes up. Restarting BNFO and lookup"
        log(msg)
        print(dt.now(),msg)
    msg = "Time up . exiting BNFO Lookup"
    print(dt.now(),msg)
    log(msg)
    
