"""
Modifed on Fri Feb 28 22:35:14 2020

@author: Thennan

"""


import urllib.request
import shutil
import pandas as pd
import numpy as np
import MySQLdb
from sendMailV1 import mailer as mail
from datetime import datetime as dt, date, timedelta as tDelta
import calendar
from os import path,makedirs
import json


credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)
mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']

oneDay = tDelta(days=1)
oneWeek = tDelta(days=7)
lastThursMsg = ''


def yesterdayLastThursday(inDate1):    
    inDate1 = dt.strptime(str(inDate1), '%Y-%m-%d').date()
    inDate1 = inDate1 - oneDay
    lastDayofMonth = calendar.monthrange(inDate1.year,inDate1.month)[1]
    lastDateOfTheMonth = (inDate1.replace(day = lastDayofMonth))
    lastThursday = lastDateOfTheMonth    
    while lastThursday.weekday() != calendar.THURSDAY:
        lastThursday = lastThursday-oneDay        
    if inDate1 == lastThursday:
        return True
    else:
        return False


def lookup():
    
    def log(txt):
    	directory = path.join('Logs',str(date.today())+'_DAS5Logs')
    	if not path.exists(directory):
    		makedirs(directory)
    	logFile = path.join(directory,str(date.today())+'_Lookup.log')
    	logMsg = '\n'+str(dt.now())+'    ' + txt
    	with open(logFile,'a') as f:
    		f.write(logMsg)              
    
    try:
        
        ##Checking if Today is next day after lastThursday and updating the instrument lookup File##
        if yesterdayLastThursday(dt.today().date()):
            log('Yesterday was the last Thursday of the Month. will attempt to update FUT File')
            yestDay = dt.today() - oneDay
            nextWeek = dt.today() + oneWeek    
            lMonth = yestDay.strftime("%b").upper()
            nMonth = nextWeek.strftime("%b").upper()    
            nextInd = str(nextWeek.year)[-2:] + nMonth + 'FUT'   
            log('Next Index suffix : '+nextInd)
            nNifty = 'NIFTY'+nextInd
            nBankNifty = 'BANKNIFTY'+nextInd
            currFile = path.join('lookup_tables','instrumentsLookup.xlsx')
            oldFile = path.join('lookup_tables','instrumentsLookup_'+lMonth+str(yestDay.year)+'.xlsx')
            shutil.copy(currFile,oldFile)
            log('Old Instrument File backed up. Old File Name : ' + oldFile )
            instrumentTables = pd.read_excel(path.join('lookup_tables','instrumentsLookup.xlsx'))        
            instrumentTables.loc[instrumentTables.Table == 'NIFTYFUT', 'Symbol'] = nNifty
            instrumentTables.loc[instrumentTables.Table == 'BANKNIFTYFUT', 'Symbol'] = nBankNifty        
            instrumentTables.to_excel(path.join('lookup_tables','instrumentsLookup.xlsx'),index = False) 
            lastThursMsg = 'Yesterday was the last Thursday of the Month. nNifty => '+nNifty+' nBankNifty  => '+nBankNifty
        else:
            log('Yesterday was NOT the last Thursday of the Month')
            lastThursMsg = 'Yesterday was NOT the last Thursday of the Month'
             ##FUT Update Over##
        
        
        #Downloading the instrument list
        lookupDirectory = 'lookup_tables'
        if not path.exists(lookupDirectory):
            makedirs(lookupDirectory)
        tslice = str(date.today())
        fname = path.join('lookup_tables','instruments_'+tslice+'.csv')
        urllib.request.urlretrieve('https://api.kite.trade/instruments', fname)

        #Importing only the required columns
        allInst = pd.read_csv(fname,usecols=['instrument_token','tradingsymbol','instrument_type','exchange'])     
        
        #Smaller dataframes
        ##NSE and NFO Only
        allInst = allInst[allInst['exchange'].isin(['NSE','NFO'])]
        allInst = allInst[allInst['instrument_type'].isin(['EQ','FUT'])]
              
        ##Reading instruments to be subscribed     
        symbols = pd.read_excel(path.join('lookup_tables','instrumentsLookup.xlsx'))['Symbol'].values.tolist()
        tables = pd.read_excel(path.join('lookup_tables','instrumentsLookup.xlsx'))['Table'].values.tolist()
             
        ## retaining desired symbols only and dropping exchange
        inst = allInst[allInst['tradingsymbol'].isin(symbols)].drop('exchange',axis=1)
        inst = inst.drop('instrument_type',axis=1)
        inst = inst.drop_duplicates()
        
        ##Reading the lookup table again to create lookup disctionary
        instrumentTables = pd.read_excel(path.join('lookup_tables','instrumentsLookup.xlsx'),usecols="A,B")
        instrumentTableReplace = instrumentTables.set_index('Symbol')['Table'].to_dict()
        inst.replace(instrumentTableReplace,inplace=True)	
        
        tokenTable= inst.set_index('instrument_token')['tradingsymbol'].to_dict()        
        
        #Token:Symbol Dictionary
        
        np.save(path.join('lookup_tables','nseTokenTable.npy'), tokenTable)        
        #Instrumnet_Token_List Dictionary
        inst.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','nseTokenList.csv'),index=False)		


####DAS5_2 A.K.A DAS7_1     
        
        symbols2 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_2.xlsx'))['Symbol'].values.tolist()
        tables2 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_2.xlsx'))['Table'].values.tolist()       
        
        ## retaining desired symbols only and dropping exchange
        inst2 = allInst[allInst['tradingsymbol'].isin(symbols2)].drop('exchange',axis=1)
        inst2 = inst2.drop('instrument_type',axis=1)
        inst2 = inst2.drop_duplicates()
        
        ##Reading the lookup table again to create lookup disctionary
        instrumentTables2 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_2.xlsx'),usecols="A,B")
        instrumentTableReplace2 = instrumentTables2.set_index('Symbol')['Table'].to_dict()
        inst2.replace(instrumentTableReplace2,inplace=True)	
        
        tokenTable2= inst2.set_index('instrument_token')['tradingsymbol'].to_dict()        
        
        #Token:Symbol Dictionary
        
        np.save(path.join('lookup_tables','nseTokenTable2.npy'), tokenTable2)        
        #Instrumnet_Token_List Dictionary
        inst2.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','nseTokenList2.csv'),index=False)	
        
####DAS5_3 A.K.A DAS7_2     
        
        symbols3 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_3.xlsx'))['Symbol'].values.tolist()
        tables3 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_3.xlsx'))['Table'].values.tolist()               


        ## retaining desired symbols only and dropping exchange
        inst3 = allInst[allInst['tradingsymbol'].isin(symbols3)].drop('exchange',axis=1)
        inst3 = inst3.drop('instrument_type',axis=1)
        inst3 = inst3.drop_duplicates()
        
        ##Reading the lookup table again to create lookup disctionary
        instrumentTables3 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_3.xlsx'),usecols="A,B")
        instrumentTableReplace3 = instrumentTables3.set_index('Symbol')['Table'].to_dict()
        inst3.replace(instrumentTableReplace3,inplace=True)	
        
        tokenTable3= inst3.set_index('instrument_token')['tradingsymbol'].to_dict()        
        
        #Token:Symbol Dictionary
        
        np.save(path.join('lookup_tables','nseTokenTable3.npy'), tokenTable3)        
        #Instrumnet_Token_List Dictionary
        inst3.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','nseTokenList3.csv'),index=False)	

####DAS5_4 A.K.A DAS7_3
        symbols4 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_4.xlsx'))['Symbol'].values.tolist()
        tables4 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_4.xlsx'))['Table'].values.tolist()          
        ## retaining desired symbols only and dropping exchange
        inst4 = allInst[allInst['tradingsymbol'].isin(symbols4)].drop('exchange',axis=1)
        inst4 = inst4.drop('instrument_type',axis=1)
        inst4 = inst4.drop_duplicates()
        
        ##Reading the lookup table again to create lookup disctionary
        instrumentTables4 = pd.read_excel(path.join('lookup_tables','instrumentsLookup_DAS5_4.xlsx'),usecols="A,B")
        instrumentTableReplace4 = instrumentTables4.set_index('Symbol')['Table'].to_dict()
        inst4.replace(instrumentTableReplace4,inplace=True)	
        
        tokenTable4= inst4.set_index('instrument_token')['tradingsymbol'].to_dict()        
        
        #Token:Symbol Dictionary
        
        np.save(path.join('lookup_tables','nseTokenTable4.npy'), tokenTable4)        
        #Instrumnet_Token_List Dictionary
        inst4.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','nseTokenList4.csv'),index=False)	        
		
		##Index Tables##
		##Index Tables##
        indices = pd.read_excel(path.join('lookup_tables','Index_Table.xls'))['Symbol'].values.tolist()
        indicInst = allInst[allInst['tradingsymbol'].isin(indices)].drop('exchange',axis=1)
        indicInst = indicInst.drop_duplicates()
		
        indexTable = pd.read_excel(path.join('lookup_tables','Index_Table.xls'),usecols="A,B")
        indexTableReplace = indexTable.set_index('Symbol')['Table_Name'].to_dict()
        indicInst.replace(indexTableReplace,inplace=True)
        indextable = indicInst.set_index('instrument_token')['tradingsymbol'].to_dict()
		
		#Token:Symbol Dictionary - Indices
        np.save(path.join('lookup_tables','indextable.npy'), indextable)
        #Instrumnet_Token_List 
        indicInst.drop('tradingsymbol',axis=1).to_csv(path.join('lookup_tables','indexTokenList.csv'),index=False)
		
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()
        
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das4daily")
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das4")
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das2daily")
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das2")
        
        
        tables = tables+tables2+tables3+tables4
        
        for tb in tables:
            c.execute("CREATE TABLE IF NOT EXISTS aws_das4daily.`"+tb+"` \
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
            
            c.execute("CREATE TABLE IF NOT EXISTS aws_das4.`"+tb+"` \
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
			
        c.execute("create table if not exists aws_das2daily.BANKNIFTY (timestamp DATETIME UNIQUE,price decimal(12,2))")
        c.execute("create table if not exists aws_das2daily.NIFTY (timestamp DATETIME UNIQUE,price decimal(12,2))") 			

        c.close()
        conn.close()
		
	
        msg = 'DAS5 Started.Token Lookup Successful '+lastThursMsg
        log(msg)
        print(msg)
        mail(creds['destinationEmailAddress'],msg,'DAS5: Instrument Token Lookup succeeded at '+str(dt.now())+'\n Proceeding to Dumps')
        return True

    except Exception as e:
        log(str(e))
        print("Instrument Token Lookup Failed "+str(e))
        mail(creds['destinationEmailAddress'], 'DAS5: Instrument Token Lookup Failed',str(e))
        return False