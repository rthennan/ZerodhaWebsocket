"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Downloads Instrument List from Zerodha
Lists the exchange tokens (instrument_token) to be subscribed, based on the lookup table Generated / Updated by nifty500Updater
Estimate current and next expiry dates for Nifty and BankNifty Options
Generates Instrument Token Lists for 
    - NiftyOptions - current and next expiry 
    - BankNiftyOptions - current and Next expiry 
Creates lookup Dictionaries that will be used for exchangeToken => TableName and exchangeToken => Symbol in the actual ticker
Creates DB and one table for storing daily tick. Can be used for live queries during market hours
Table:
    {nifty500DBName}.dailytable
Example queries to get data from live DB (live Ticks):
    SELECT timestamp, price FROM dailytable WHERE tradingsymbol='NIFTY 50' order by timestamp DESC LIMIT 5;
    SELECT timestamp, price FROM dailytable WHERE tablename='NIFTY' order by timestamp DESC LIMIT 5;
    SELECT instrument_token, timestamp, price, volume FROM dailytable WHERE tradingsymbol='NIFTY24APRFUT' order by timestamp DESC LIMIT 5;
    SELECT timestamp, price, volume FROM dailytable WHERE tablename='NIFTYFUT' order by timestamp DESC LIMIT 5;
    SELECT timestamp, price, volume FROM dailytable WHERE instrument_token=13368834 order by timestamp DESC LIMIT 5;
nifty500DBName configured in dasConfig.json

Some of the operations for Nifty500 token and Options tokens, 
lookup table creation and SQL table creation could have been combined.
combined vs 3 separate lookup tables for ~1300 tokens doesn't have any measurable performance difference.
But splitting them on purpose, for readability.
Also, if you don't want a part of the ticker, 
you could just remove it from here and the main ticker - DAS_ticker

Check _InstrumentsSubscribed.log to see the list of symbols subscribed to

#Change log - 2024-04-08:
    - DAS_Ticker now stores live ticks into one table now. This is to reduce IOPS
    - Hence only creating one table, instead of the previous 'one table per instrument' approach 

"""
import pandas as pd
import numpy as np
import MySQLdb
from datetime import datetime as dt, date, timedelta
from dateutil.relativedelta import relativedelta, TH, WE
from os import path,makedirs
import json
from DAS_gmailer import DAS_mailer
import traceback
from DAS_errorLogger import DAS_errorLogger
from time import sleep
import sys
import urllib.request
from isDasConfigDefault import isDasConfigDefault
numbOfRetries = 5

configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)
destinationEmailAddress = dasConfig['destinationEmailAddress']
mysqlHost = dasConfig['mysqlHost']
mysqlUser = dasConfig['mysqlUser']
mysqlPass = dasConfig['mysqlPass']
mysqlPort = dasConfig['mysqlPort']

dailyTableName = 'dailytable'
nifty500DBName = dasConfig['nifty500DBName']

lookupDirectory = 'lookupTables'
n500instrumentLookupFile = 'lookupTables_Nifty500.csv'
n500InstrumentFilePath = path.join(lookupDirectory,n500instrumentLookupFile)
    
def lookupTableCreatorLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_lookupTableCreator_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)
        
def insrumentListLogger(txt):
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_InstrumentsSubscribed_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)

def downloadZerodhaInstrumentFile():
    zerodhaDumpUrl = 'https://api.kite.trade/instruments'
    zerdhaIstrumentDumpFileName = 'zerodhaInstrumentDump.csv'
    zerdhaIstrumentDumpFilePath = path.join('lookupTables',zerdhaIstrumentDumpFileName)
    for attempt in range(1,numbOfRetries+1):
        try:    
            urllib.request.urlretrieve(zerodhaDumpUrl, zerdhaIstrumentDumpFilePath)            
            msg = 'Downloaded Instrument dump file from Zerodha'
            lookupTableCreatorLogger(msg)   
            return None
        except Exception as e:
            msg = f'Downloading zerodhaInstrumentsDump from {zerodhaDumpUrl} Failed. Attempt No :{attempt} . Exception-> {e} Traceback : {traceback.format_exc()}.\nWill retry after 30 seconds'
            lookupTableCreatorLogger(msg)
            DAS_errorLogger('lookupTablesCreator - '+msg)
            sleep(30)
        else:
            break
    else:
        msg = f'Downloading zerodhaInstrumentsDump from {zerodhaDumpUrl} Failed after {numbOfRetries} attempts. Exiting'
        lookupTableCreatorLogger(msg)
        DAS_errorLogger('lookupTablesCreator - '+msg)
        sys.exit()


#zerdhaIstrumentDumpFile is used multiple times
#Nifty 500 - Once for getting instrument_tokens
#Nifty Options - Thrice - Once for each each expiry and once for getting instrument_tokens
#BankNifty Options - Thrice - Once for each each expiry and once for getting instrument_tokens
#So retaining and using a local file if it is fresh
def getZerodhaInstDump():
    zerdhaIstrumentDumpFileName = 'zerodhaInstrumentDump.csv'
    zerdhaIstrumentDumpFilePath = path.join('lookupTables',zerdhaIstrumentDumpFileName)
    if path.exists(zerdhaIstrumentDumpFilePath):
        oneHourAgo = dt.now() - timedelta(hours=1)
        #if file exists and is fresh (not older than an hour), use the local file.
        zerodhaDumpModifiedTime = dt.fromtimestamp(path.getmtime(zerdhaIstrumentDumpFilePath))
        if zerodhaDumpModifiedTime >= oneHourAgo:
            msg = f'local zerdhaIstrumentDumpFile {zerdhaIstrumentDumpFileName} is fresh. Using it.'
            lookupTableCreatorLogger(msg)
        else:
            msg = f'local zerodhaInstrumentDumpFile {zerdhaIstrumentDumpFileName} is older than 1 hour. Downloading a new one'
            lookupTableCreatorLogger(msg)
            downloadZerodhaInstrumentFile()
    else:
        msg = f'local zerodhaInstrumentDumpFile {zerdhaIstrumentDumpFileName} not found. Downloading a new one'
        lookupTableCreatorLogger(msg)
        downloadZerodhaInstrumentFile()
       
    return pd.read_csv(zerdhaIstrumentDumpFilePath)
    
def getNiftyExpiry(inDate):
    #Uses global variable zerodhaInstrumentsDump
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    #Filtering Nifty Options from zerodhaInstrumentsDump
    zerodhaInstrumentsDump = getZerodhaInstDump()
    niftyOptions = zerodhaInstrumentsDump[zerodhaInstrumentsDump['segment'].isin(['NFO-OPT'])]
    niftyOptions = niftyOptions[niftyOptions['name'].isin(['NIFTY'])]
    #Filtering just CE as we interested only in the expiry dates now and not the actual instruments
    niftyOptions = niftyOptions[niftyOptions['instrument_type'].isin(['CE'])]
    niftyExpiyDates = sorted(list(niftyOptions['expiry'].unique()))

    thisThursday = inDate + relativedelta(weekday=TH(0))
    niftyExpiryDate = thisThursday
    
    #Check if thisThursday is in the nifty expiry dates.
    #If thursday is a Holiday, the previous TRADING day would be the expiry.
    #Keep decrementing the date till it is found in the expiry dates
    while str(niftyExpiryDate) not in niftyExpiyDates:
        niftyExpiryDate = niftyExpiryDate - timedelta(days=1)
    return str(niftyExpiryDate)  

def getBankNiftyExpiry(inDate):
    #Uses global variable zerodhaInstrumentsDump
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    #Filtering Nifty Options from zerodhaInstrumentsDump
    zerodhaInstrumentsDump = getZerodhaInstDump()
    bankNiftyOptions = zerodhaInstrumentsDump[zerodhaInstrumentsDump['segment'].isin(['NFO-OPT'])]
    bankNiftyOptions = bankNiftyOptions[bankNiftyOptions['name'].isin(['BANKNIFTY'])]
    #Filtering just CE as we interested only in the expiry dates now and not the actual instruments
    bankNiftyOptions = bankNiftyOptions[bankNiftyOptions['instrument_type'].isin(['CE'])]
    bankNiftyExpiyDates = sorted(list(bankNiftyOptions['expiry'].unique()))

    thisWednesday = inDate + relativedelta(weekday=WE(0))
    bankNiftyExpiryDate = thisWednesday
    
    #Check if thisWednesday is in the nifty expiry dates.
    #If Wednesday is a Holiday, the previous TRADING day would be the expiry.
    #Keep decrementing the date till it is found in the expiry dates
    while str(bankNiftyExpiryDate) not in bankNiftyExpiyDates:
        bankNiftyExpiryDate = bankNiftyExpiryDate - timedelta(days=1)
    return str(bankNiftyExpiryDate)  

def lookupTablesCreatorNifty500():
    try:
        
        '''
        =========================================
        Creating Lookup Tables for Nifty500 - Start
        =========================================
        '''
        msg = 'DAS - Nifty 500 Lookup Table Creation Started'
        lookupTableCreatorLogger(msg)
        
        ##Reading Nifty500 instruments +Index + IndexFuture to be subscribed
        ##Reading the lookup table again to create lookup dictionary
        n500InstrumentSymbolsTables = pd.read_csv(n500InstrumentFilePath)
        n500InstrumentSymbols = n500InstrumentSymbolsTables['Symbol'].values.tolist()
    
        #Downloading Zerodha Instrument dump 
        zerodhaInstrumentsDump = getZerodhaInstDump()
        
        ## retaining instrument_token and tradingsymbol only in the instrument dump
        nifty500Instruments = zerodhaInstrumentsDump[zerodhaInstrumentsDump['tradingsymbol'].isin(n500InstrumentSymbols)]
        #Filtering further.
        #'exchange'.isin(['NSE','NFO']
        #'instrument_type'.isin(['EQ','FUT']
        nifty500Instruments = nifty500Instruments[nifty500Instruments['exchange'].isin(['NSE','NFO'])]
        nifty500Instruments = nifty500Instruments[nifty500Instruments['instrument_type'].isin(['EQ','FUT'])]
        
        ##Retaining instrument_token and tradingsymbol only from the instrument dump 
        nifty500Instruments = nifty500Instruments[['instrument_token','tradingsymbol']]
        nifty500Instruments = nifty500Instruments.drop_duplicates()
        
        #Creating a lookup dictionary for Symbols. Lookup the exchange token, get the Symbol response
        n500TokenSymbolDict= nifty500Instruments.set_index('instrument_token')['tradingsymbol'].to_dict()  
        #Saving the exchange_token:Symbol Dictionary
        np.save(path.join(lookupDirectory,'nifty500TokenSymbolDict.npy'), n500TokenSymbolDict)
        msg = 'Saved n500TokenTable exchange_token:Symbol Dictionary => nifty500TokenSymbolDict.npy'
        lookupTableCreatorLogger(msg)        
        
        ##Creating a lookup dictionary - Lookup Symbol, get TableName
        nifty500TableNameLookup = n500InstrumentSymbolsTables.set_index('Symbol')['TableName'].to_dict()
        #In the original instrument dump, replacing the symbol with the table name.
        #This way, in the ticker, any response for the instrument_token is stored to its table directly.
        #This is necessary as the table name is not the same as the symbol name for a few instruments:
            #Symbol has special character (M&M)
        #The tradingsymbol column now holds the Table Name
        nifty500Instruments = nifty500Instruments.rename(columns={'tradingsymbol': 'TableName'})
        nifty500Instruments.replace(nifty500TableNameLookup,inplace=True)
        
        #Creating a lookup dictionary from this.
        #Lookup the exchange token, get the table name as response
        #The tradingsymbol column now holds the Table Name
        n500TokenTableDict= nifty500Instruments.set_index('instrument_token')['TableName'].to_dict()
        
        #Saving the exchange_token:TableName Dictionary
        np.save(path.join(lookupDirectory,'nifty500TokenTableDict.npy'), n500TokenTableDict)
        msg = 'Saved n500TokenTable exchange_token:TableName Dictionary => nifty500TokenTableDict.npy'
        lookupTableCreatorLogger(msg)
        
        #Separating Indexes NIFTY and BANKNIFTY from the main list
        #They have just two columns in the feed - timestamp and price.
        #Don't have to be removed from the main list.
        #just a list to check and create different table structure at EoD
        indexInstruments = nifty500Instruments.loc[nifty500Instruments['TableName'].isin(['NIFTY', 'BANKNIFTY'])]
        indexInstruments.drop('TableName',axis=1).to_csv(path.join(lookupDirectory,'indexTokenList.csv'),index=False)	
        msg = 'Saved indexTokenList.csv to differentiate Indexes Nifty and BankNifty from the other instruments for SQL store'
        lookupTableCreatorLogger(msg)
        #Saving the main exchange_token list to subscribe later
        nifty500Instruments.drop('TableName',axis=1).to_csv(path.join(lookupDirectory,'nifty500TokenList.csv'),index=False)		
        msg = 'Saved nifty500TokenList.csv'
        lookupTableCreatorLogger(msg)
        msg = f'Nifty 500 - Subscribing to {len(nifty500Instruments)} Instruments'
        lookupTableCreatorLogger(msg)
        insrumentListLogger(msg)
        # Creating a string from the 'TableName' column where each item is on a new line
        n500InstrumentNameString = '\n'.join(n500InstrumentSymbols)
        msg = 'Nifty 500 Instruments Subscribed :\n'+n500InstrumentNameString
        insrumentListLogger(msg)

        return True
    except Exception as e:
        msg = f"Instrument Token Lookup Table Creator - Nifty 500 - failed with exception {e}. Traceback : {str(traceback.format_exc())}"
        lookupTableCreatorLogger(msg)
        DAS_errorLogger('lookupTablesCreator - '+msg)
        DAS_mailer('DAS Nifty 500 Lookup Table Creator Failed',msg)
        return False
        '''
        =========================================
        Creating Lookup Tables for Nifty500 - End
        =========================================
        '''        
        
def lookupTablesCreatorNiftyOptions():
        '''        
        =========================================
        Creating Lookup Tables for Nifty Options - Start
        =========================================
        '''
        msg = 'DAS - Nifty Options Lookup Table Creation Started'
        lookupTableCreatorLogger(msg)
        try:
        
            niftyThisExpiry = getNiftyExpiry(date.today()) #This Expiry
            niftyNextExpiry = getNiftyExpiry(date.today()+timedelta(days=7)) #Next Expiry
            
            #Downloading Zerodha Instrument dump 
            zerodhaInstrumentsDump = getZerodhaInstDump()
            
            #Filtering Nifty Options from zerodhaInstrumentsDump
            niftyOptionsDF = zerodhaInstrumentsDump[zerodhaInstrumentsDump['segment'].isin(['NFO-OPT'])]
            niftyOptionsDF = niftyOptionsDF[niftyOptionsDF['name'].isin(['NIFTY'])]
            
            #Retain this and Next Expiry only
            niftyOptionsDF = niftyOptionsDF[niftyOptionsDF['expiry'].isin([niftyThisExpiry,niftyNextExpiry])]
            
            ##Retaining instrument_token and tradingsymbol only from the instrument dump 
            niftyOptionsDF = niftyOptionsDF[['instrument_token','tradingsymbol']]
            niftyOptionsDF = niftyOptionsDF.drop_duplicates()
            
            #Trading Symbol can be used as tableName as Index option symbols do not have special characters or spaces
            niftyOptionsDF = niftyOptionsDF.rename(columns={'tradingsymbol': 'TableName'})
            
            ##Creating a lookup dictionary - Lookup instrument_token, get TableName
            niftyOptionsTokenTable = niftyOptionsDF.set_index('instrument_token')['TableName'].to_dict()
    
            #Saving the exchange_token:TableName Dictionary
            #Same dictionary can be used for instrument_token:Symbol lookup for options
            np.save(path.join(lookupDirectory,'niftyOptionsTokenTableDict.npy'), niftyOptionsTokenTable)
            msg = 'Saved niftyOptionsTokenTable exchange_token:TableName Dictionary => niftyOptionsTokenTableDict.npy'
            lookupTableCreatorLogger(msg)
            
            #Saving niftyOptions instrument_token list to subscribe.
            #This will also be used to save nifty option ticks to a separate DB
            niftyOptionsDF.drop('TableName',axis=1).to_csv(path.join(lookupDirectory,'niftyOptionsTokenList.csv'),index=False)	
            msg = f'Subscribing to {len(niftyOptionsDF)} Nifty Options. Saved niftyOptionsTokenList.csv'
            lookupTableCreatorLogger(msg)
            insrumentListLogger(msg)
            # Creating a string from the 'TableName' column where each item is on a new line
            niftyOptionsNameString = '\n'.join(niftyOptionsDF['TableName'].astype(str))
            msg = 'Nifty Option Instruments Subscribed :\n'+niftyOptionsNameString
            insrumentListLogger(msg)

            return True
        except Exception as e:
            msg = f"Instrument Token Lookup Table Creator - Nifty Options - failed with exception {e}. Traceback : {str(traceback.format_exc())}"
            lookupTableCreatorLogger(msg)
            DAS_errorLogger('lookupTablesCreator - '+msg)
            DAS_mailer('DAS Nifty Options Lookup Table Creator Failed',msg)
            return False            

        '''
        =========================================
        Creating Lookup Tables for Nifty Options - End
        =========================================
        '''            

def lookupTablesCreatorBankOptions():
        '''        
        =========================================
        Creating Lookup Tables for BankNifty Options - Start
        =========================================               
        '''    
        msg = 'DAS - BankNifty Options Lookup Table Creation Started'
        lookupTableCreatorLogger(msg)
        try:        
            bankNiftyThisExpiry = getBankNiftyExpiry(date.today()) #This Expiry
            bankNiftyNextExpiry = getBankNiftyExpiry(date.today()+timedelta(days=7)) #Next Expiry
            
            #Downloading Zerodha Instrument dump 
            zerodhaInstrumentsDump = getZerodhaInstDump()
            
            #Filtering Nifty Options from zerodhaInstrumentsDump
            bankNiftyOptionsDF = zerodhaInstrumentsDump[zerodhaInstrumentsDump['segment'].isin(['NFO-OPT'])]
            bankNiftyOptionsDF = bankNiftyOptionsDF[bankNiftyOptionsDF['name'].isin(['BANKNIFTY'])]
            
            #Retain this and Next Expiry only
            bankNiftyOptionsDF = bankNiftyOptionsDF[bankNiftyOptionsDF['expiry'].isin([bankNiftyThisExpiry,bankNiftyNextExpiry])]
            
            ##Retaining instrument_token and tradingsymbol only from the instrument dump 
            bankNiftyOptionsDF = bankNiftyOptionsDF[['instrument_token','tradingsymbol']]
            bankNiftyOptionsDF = bankNiftyOptionsDF.drop_duplicates()
            
            #Trading Symbol can be used as tableName as Index option symbols do not have special characters or spaces
            bankNiftyOptionsDF = bankNiftyOptionsDF.rename(columns={'tradingsymbol': 'TableName'})
            
            ##Creating a lookup dictionary - Lookup instrument_token, get TableName
            bankNiftyOptionsTokenTable = bankNiftyOptionsDF.set_index('instrument_token')['TableName'].to_dict()

            #Saving the exchange_token:TableName Dictionary
            #Same dictionary can be used for instrument_token:Symbol lookup for options
            np.save(path.join(lookupDirectory,'bankNiftyOptionsTokenTableDict.npy'), bankNiftyOptionsTokenTable)
            msg = 'Saved bankNiftyOptionsTokenTable exchange_token:TableName Dictionary => bankNiftyOptionsTokenTableDict.npy'
            lookupTableCreatorLogger(msg)
            
            #Saving BankNiftyOptions instrument_token list to subscribe.
            #This will also be used to save nifty option ticks to a separate DB
            bankNiftyOptionsDF.drop('TableName',axis=1).to_csv(path.join(lookupDirectory,'bankNiftyOptionsTokenList.csv'),index=False)	
            msg = f'Subscribing to {len(bankNiftyOptionsDF)} BankNifty Options. Saved bankNiftyOptionsTokenList.csv'
            lookupTableCreatorLogger(msg)
            insrumentListLogger(msg)
            # Creating a string from the 'TableName' column where each item is on a new line
            bankNiftyOptionsNameString = '\n'.join(bankNiftyOptionsDF['TableName'].astype(str))
            msg = 'Bank Nifty Option Instruments Subscribed :\n'+bankNiftyOptionsNameString
            insrumentListLogger(msg)
            return True
        except Exception as e:
            msg = f"Instrument Token Lookup Table Creator - BankNifty Options - failed with exception {e}. Traceback : {str(traceback.format_exc())}"
            lookupTableCreatorLogger(msg)
            DAS_errorLogger('lookupTablesCreator - '+msg)
            DAS_mailer('DAS BankNifty Options Lookup Table Creator Failed',msg)
            return False   
        '''
        =========================================
        Creating Lookup Tables for Bank Nifty Options - End
        =========================================
        '''          
def lookupTablesCreator():    
    if isDasConfigDefault():
        msg = 'DAS Config has defaults. accessTokenReq is exiting'
        lookupTableCreatorLogger(msg)
        DAS_errorLogger(msg)
        return False
    #On failure, function would have exited at the False return.
    #Hence no Else required here
    n500TablesCreated = lookupTablesCreatorNifty500()
    niftyOptionsTablesCreated = lookupTablesCreatorNiftyOptions()
    bankOptionsTablesCreated = lookupTablesCreatorBankOptions()
    
    if not all([n500TablesCreated, niftyOptionsTablesCreated, bankOptionsTablesCreated]):
        msg = 'One or more Lookup Table Creation Activities FAILED!!!'
        lookupTableCreatorLogger(msg)  
        DAS_errorLogger('lookupTablesCreator - '+msg)
        return False   
        
    if n500TablesCreated and niftyOptionsTablesCreated and bankOptionsTablesCreated:
        #Create {nifty500DBName}
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
        c = conn.cursor() 
        c.execute(f'CREATE DATABASE IF NOT EXISTS {nifty500DBName}')
        
        ##Create Daily table - {nifty500DBName}.{dailyTableName} 
        
        c.execute(f'''
                    CREATE TABLE IF NOT EXISTS {nifty500DBName}.{dailyTableName} (
                        instrument_token BIGINT(20), 
                        tradingsymbol VARCHAR(100),
                        tablename VARCHAR(100),
                        dbname VARCHAR(100),
                        timestamp DATETIME, price DECIMAL(19,2), 
                        qty INT UNSIGNED,
                        avgPrice DECIMAL(19,2),
                        volume BIGINT,
                        bQty INT UNSIGNED,
                        sQty INT UNSIGNED,  
                        open DECIMAL(19,2),
                        high DECIMAL(19,2),
                        low DECIMAL(19,2),
                        close DECIMAL(19,2),
                        changeper DECIMAL(60,10),
                        lastTradeTime DATETIME,
                        oi INT,
                        oiHigh INT,
                        oiLow INT,  
                        bq0 INT UNSIGNED, bp0 DECIMAL(19,2), bo0 INT UNSIGNED,
                        bq1 INT UNSIGNED, bp1 DECIMAL(19,2), bo1 INT UNSIGNED,
                        bq2 INT UNSIGNED, bp2 DECIMAL(19,2), bo2 INT UNSIGNED,
                        bq3 INT UNSIGNED, bp3 DECIMAL(19,2), bo3 INT UNSIGNED,
                        bq4 INT UNSIGNED, bp4 DECIMAL(19,2), bo4 INT UNSIGNED,  
                        sq0 INT UNSIGNED, sp0 DECIMAL(19,2), so0 INT UNSIGNED,
                        sq1 INT UNSIGNED, sp1 DECIMAL(19,2), so1 INT UNSIGNED,                    
                        sq2 INT UNSIGNED, sp2 DECIMAL(19,2), so2 INT UNSIGNED,                    
                        sq3 INT UNSIGNED, sp3 DECIMAL(19,2), so3 INT UNSIGNED,                    
                        sq4 INT UNSIGNED, sp4 DECIMAL(19,2), so4 INT UNSIGNED,
                        UNIQUE (instrument_token, timestamp),
                        INDEX tablenameindex (tablename),
                        INDEX symbolindex (tradingsymbol),
                        INDEX instrument_token_index (instrument_token),
                        INDEX timestamp_index (timestamp)
                    )''')
        
        msg = 'DAS - All Lookup Table Creation Activities Successful'
        lookupTableCreatorLogger(msg)          
        return True
    #Catch all
    return False
    
if __name__ == '__main__':
    lookupTablesCreator()