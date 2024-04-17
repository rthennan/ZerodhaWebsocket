"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Logs in to Kite with the latest access token found in {accessTokenDBName}.kite1tokens
Gets instrument_tokens from nifty500TokenList.csv, indexTokenList.csv, niftyOptionsTokenList.csv and bankNiftyOptionsTokenList.csv in the lookupTables directory.
Subscribes to all of them in FULL mode
Uses nifty500TokenTable.npy, niftyOptionsTokenTable.npy and bankNiftyOptionsTokenTable.npy to identify the tables to which the tick data should be stored
Uses different SQL statements for Indexes and the rest of the instruments as Index ticks have fewer columns.

kiteConnect ticker field name changes in v4 and later.
https://github.com/zerodha/pykiteconnect?tab=readme-ov-file#v4---breaking-changes
Incorporated already and tested in KiteConnect Version : 5.0.1
The DB Tables would still be created with the old names to avoid major table alterations on existing setups.
So this is just for reference.
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
from sqlalchemy import create_engine
from threading import Timer

configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)
apiKey = dasConfig['apiKey']
mysqlHost = dasConfig['mysqlHost']
mysqlUser = dasConfig['mysqlUser']
mysqlPass = dasConfig['mysqlPass']
mysqlPort = dasConfig['mysqlPort']
marketCloseHour = dasConfig['marketCloseHour']
marketCloseMinute = dasConfig['marketCloseMinute']

accessTokenDBName = dasConfig['accessTokenDBName']
zerodhaLoginName = dasConfig['ZerodhaLoginName'] 
dailyTableName = 'dailytable'
nifty500DBName = dasConfig['nifty500DBName']
niftyOptionsDBName = dasConfig['niftyOptionsDBName']
bankNiftyOptionsDBName = dasConfig['bankNiftyOptionsDBName']


conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
c = conn.cursor()
#Create SQL Alchemy engine for SQL insertion
#engine = create_engine(f'mysql+pymysql://{mysqlUser}:{mysqlPass}@{mysqlHost}:{mysqlPort}/{dasDailyDB}')
engine = create_engine(f'mysql+mysqldb://{mysqlUser}:{mysqlPass}@{mysqlHost}:{mysqlPort}/{nifty500DBName}')
# fast_executemany=True is specific to the pyodbc engine for connecting to Microsoft SQL Server databases, not for MySQL connections with pymysql or any other MySQL connector

def DAS_Tickerlogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_Ticker_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)

def bulkPrint(ticks):
    #for debugging 
    for tick in ticks:
        print('dict',tick)
        print('dictKeys',tick.keys())
        print('dictValues',tick.values())
        print('dictDTypes',[type(x) for x in tick.values()])
    
# Unwrap depth data or return None if not available
def preprocess_depth(ticks_df):
    ticks_df['depth'] = ticks_df['depth'].apply(lambda x: x if isinstance(x, dict) else {})
    return ticks_df

def extract_depth_values(ticks_df, side, index, key):
    """Extract depth values in a vectorized manner."""
    def extract_value(depth):
        return depth.get(side, [])[index].get(key, None) if depth else None

    # Apply the extraction function across the 'depth' column
    return ticks_df['depth'].apply(extract_value)

def getDepthValues(ticks_df):
    ticks_df = preprocess_depth(ticks_df)
    for i in range(5):
        for side, key in [('buy', 'quantity'), ('buy', 'price'), ('buy', 'orders'),
                          ('sell', 'quantity'), ('sell', 'price'), ('sell', 'orders')]:
            col_name = f"{side[0]}{key[0]}{i}"
            ticks_df[col_name] = extract_depth_values(ticks_df, side, i, key)
    return ticks_df
    
# Define the custom insert method
def replaceSQLExceuteMany(table, dfConn, keys, data_iter):   
    # Prepare the SQL insert statement as a string
    columns = ', '.join(keys)
    placeholders = ', '.join(['%s' for _ in keys])
    tableName = table.name
    insert_stmt = f"REPLACE INTO {tableName} ({columns}) VALUES ({placeholders})"
    # Convert data_iter to a list of tuples
    data = list(data_iter)
    
    # Use the raw connection to execute
    with dfConn.connection.cursor() as cursor:
        cursor.executemany(insert_stmt, data)
        dfConn.connection.commit()



def DAS_Ticker(shutdown_hour, shutdown_minute):
    msg = f'DAS_Ticker called with end time {shutdown_hour}:{shutdown_minute}'
    DAS_Tickerlogger(msg)
    # Calculate the duration to run before shutting down
    now = dt.now()
    shutdownTime = now.replace(hour=shutdown_hour, minute=shutdown_minute, second=0, microsecond=0)
    runDuration = (shutdownTime - now).total_seconds()
    #Exit if Run Duration is negative. i.e. Close time is in the past
    if runDuration <0 :
        msg = f'DAS ticker called with close time in the past. currentTime =>{now}. Shutdown time =>{shutdownTime}. Exiting'
        DAS_Tickerlogger(msg)
        DAS_errorLogger(msg)
        return False
    
    def shutdownTicker():
        # Perform any necessary cleanup, logging, or data saving here
        msg = 'Shutting Down DAS_Ticker'
        DAS_Tickerlogger(msg)
        # Close Webscoket
        #kws.close()
        #Sleep for 10 seconds to allow handshake/cleanup
        #sleep(10)
        try:
            kws.stop()
            DAS_Tickerlogger('Ticker Stopped')
        except Exception as e:
            msg = f'Ticker Could not be stopped. Exception => {e}'
            DAS_Tickerlogger(msg)
            DAS_errorLogger(msg)
            DAS_mailer('DAS Ticker - Ticker Could not be stopped!!!',msg)             
        return True

    
    # Set a timer to stop the ticker at the specified time
    shutdownTimer = Timer(runDuration, shutdownTicker)
    shutdownTimer.start()

    lookupDir = 'lookupTables'
    
    #Identify Only Nifty and BankNifty as they have a different table structure and hence different SQL stmnt
    #indexTokens = pd.read_csv(path.join(lookupDir,'indexTokenList.csv'))['instrument_token'].values.tolist()  
   
    #Nifty500 Tokens and Token Table (Lookup => instrument_token:TableName)
    #Includes Nifty 500, Nifty, BankNifty and their Futures
    nifty500Tokens = pd.read_csv(path.join(lookupDir,'nifty500TokenList.csv'))['instrument_token'].values.tolist()
    nifty500TokenTable = np.load(path.join(lookupDir,'nifty500TokenTableDict.npy'),allow_pickle=True).item() 
    nifty500TokenSymbol = np.load(path.join(lookupDir,'nifty500TokenSymbolDict.npy'),allow_pickle=True).item() 
    
    #Nifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
    niftyOptionTokens = pd.read_csv(path.join(lookupDir,'niftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
    niftyOptionsTokenTable = np.load(path.join(lookupDir,'niftyOptionsTokenTableDict.npy'),allow_pickle=True).item() 
    
    #BankNifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
    bankNiftyOptionTokens = pd.read_csv(path.join(lookupDir,'bankNiftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
    bankNiftyOptionsTokenTable = np.load(path.join(lookupDir,'bankNiftyOptionsTokenTableDict.npy'),allow_pickle=True).item() 
    
    #Combining all three token lists. Subscribing to this master list
    fullTokenList = nifty500Tokens + niftyOptionTokens + bankNiftyOptionTokens
    #Removing indexTokens for testing
    #fullTokenList = [token for token in fullTokenList if token not in indexTokens]


    
    #Retaining 3 for insert check 
    #fullTokenList = [345089,11829506]+indexTokens
    #fullTokenList = indexTokens
    
    #Combine all three token:table dictionairies
    mainTokenTableDict = {}
    mainTokenTableDict.update(nifty500TokenTable)
    mainTokenTableDict.update(niftyOptionsTokenTable)
    mainTokenTableDict.update(bankNiftyOptionsTokenTable)
    
    #Combine all three token:symbol dictionairies
    mainTokenSymbolDict = {}
    mainTokenSymbolDict.update(nifty500TokenSymbol)
    mainTokenSymbolDict.update(niftyOptionsTokenTable) #Symbol and tableName are same for nifty options
    mainTokenSymbolDict.update(bankNiftyOptionsTokenTable) #Symbol and tableName are same for BankNifty options 
    
    #Creating a lookup dictionairy for instrument_token:DBName
    tokenToDbNameDict = {token: nifty500DBName for token in nifty500Tokens}
    tokenToDbNameDict.update({token: niftyOptionsDBName for token in niftyOptionTokens})
    tokenToDbNameDict.update({token: bankNiftyOptionsDBName for token in bankNiftyOptionTokens})   
    
    def bulkReplace(ticks):
        global engine

        #Testing iteration time
        #print(dt.now(),f'About to insert list with {len(ticks)} ticks')
        try:
            # Convert list of dictionaries to DataFrame
            ticksDf = pd.DataFrame(ticks)
            
            #print(dt.now(),'Adding Trading Symbol')
            ticksDf['tradingsymbol'] = ticksDf['instrument_token'].map(mainTokenSymbolDict)
            
            #print(dt.now(),'Adding TableName')
            ticksDf['tablename'] = ticksDf['instrument_token'].map(mainTokenTableDict)
            
            #print(dt.now(),'Adding DBName')
            ticksDf['dbname']  = ticksDf['instrument_token'].map(tokenToDbNameDict)
            
            #print(dt.now(),'Unwrapping ohlc')
            # Unwrap 'ohlc' dictionary into separate columns
            ticksDf['open'] = ticksDf['ohlc'].apply(lambda x: x.get('open', None))
            ticksDf['high'] = ticksDf['ohlc'].apply(lambda x: x.get('high', None))
            ticksDf['low'] = ticksDf['ohlc'].apply(lambda x: x.get('low', None))
            ticksDf['close'] = ticksDf['ohlc'].apply(lambda x: x.get('close', None))
            
            #Dropping original ohlc column 
            ticksDf.drop(columns=['ohlc'], inplace=True)
            
            #print(dt.now(),'Done OHLC. Unwrapping depth using getDepthValues')
            #Cases were ticks are purely for index symbols
            if 'depth' not in ticksDf.columns:
                # If 'depth' column does not exist, populate bq*, bp*, bo*, sq*, sp*, and so* columns with None
                for i in range(5):
                    ticksDf[f'bq{i}'] = None
                    ticksDf[f'bp{i}'] = None
                    ticksDf[f'bo{i}'] = None
                    ticksDf[f'sq{i}'] = None
                    ticksDf[f'sp{i}'] = None
                    ticksDf[f'so{i}'] = None
            else:
                # 'depth' column exists; use getDepthValues to extract and assign data
                ticksDf = getDepthValues(ticksDf)
                #Drop original depth column
                ticksDf.drop(columns=['depth'], inplace=True, errors='ignore')
                
            #print(dt.now(),'Done Unwrapping. Renaming columns.')
            #Dropping original 'depth' column
            #Also dropping 'tradeable' and 'mode' columns
            #Depth might be missing if the ticks contain only index data
            ticksDf.drop(columns=['tradable','mode'], inplace=True, errors='ignore')
            
            #Renaming columns to match with friendly column names in the table
            ticksDf.rename(columns={
                'exchange_timestamp': 'timestamp',
                'last_price': 'price',
                'last_traded_quantity': 'qty',
                'average_traded_price': 'avgPrice',
                'volume_traded': 'volume',
                'total_buy_quantity': 'bQty',
                'total_sell_quantity': 'sQty',
                'last_trade_time': 'lastTradeTime',
                'change': 'changeper',
                'oi_day_high': 'oiHigh',
                'oi_day_low': 'oiLow'
            }, inplace=True)

            #print(dt.now(),'Done Renaming. Inserting DF to SQL.')
            # Insert the DataFrame into SQL
            #ticksDf.to_sql('dailytable', con=engine, if_exists='append', index=False, method='multi')
            
            # Use the custom method with to_sql
            ticksDf.to_sql(f'{dailyTableName}', con=engine, if_exists='append', index=False, method=replaceSQLExceuteMany)
            
            #method='multi' to reduce SQL statements, round trips and in turn Disk I/O
            #print(dt.now(),'Done inserting ticks to SQL')
            #could receive multiple ticks for the same instrument_token with the same exchange timestamp.
            #Needs to be handled separately. Make use of the auto increment index to find the latest value for each second
            
            
        except Exception as e:
            msg = f'DAS Ticker - bulkReplace failed for {ticks}. Exception : {e}. Traceback :  {str(traceback.format_exc())}'  
            DAS_Tickerlogger(msg)
            DAS_errorLogger('DAS_Ticker - '+msg)
            DAS_mailer('DAS Ticker - Dump Failed.',msg)   
    
            
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
            #for tick in ticks: #for debug
            #    bulkPrint(ticks)
            bulkReplace(ticks)
                
            
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
        
if __name__ == '__main__':
    #Create main daily database
    c.execute(f'CREATE DATABASE IF NOT EXISTS {nifty500DBName}')
    
    '''
    ticksDf.to_sql is capable of creating the table as well.
    But if for some reason you only the index (NIFTY50, BANK) tokens, the table created will have lesser columns.
    As a result, if you try to store non-index (NIFTY50, BANK) tokens to this table, it will fail
    Sometimes tick includes updated data for the same timestamp. Will result in duplicates if stored as is.
    Hence doing UNIQUE (instrument_token, timestamp) .
    Actual SQL used under the hood is REPLACE INTO. This allows querying from dailyTableName live, without much complexity.
    Filter on tablename or symbol to get actual data.
    Examples:
        SELECT timestamp, price FROM dailytable WHERE tradingsymbol='NIFTY 50' order by timestamp DESC LIMIT 5;
        SELECT timestamp, price FROM dailytable WHERE tablename='NIFTY' order by timestamp DESC LIMIT 5;
        SELECT timestamp, price, volume FROM dailytable WHERE tradingsymbol='NIFTY24APRFUT' order by timestamp DESC LIMIT 5;
        SELECT timestamp, price, volume FROM dailytable WHERE tablename='NIFTYFUT' order by timestamp DESC LIMIT 5;
        SELECT timestamp, price, volume FROM dailytable WHERE instrument_token=13368834 order by timestamp DESC LIMIT 5;        
    
    Also enforcing column names, datatypes and structure
    
    column dbname is of no use for live data.
    Creating in case it can be used later to further optimize the daily backup task

    Renamed tick columns whilr storing to DB
        #exchange_timestamp to timestamp
        #last_price to price
        #last_traded_quantity to qty
        #average_traded_price to avgPrice
        #volume_traded to volume
        #total_buy_quantity to bQty
        #total_sell_quantity to sQty
        #last_trade_time to lastTradeTime
        #change to changeper
        #oi_day_high to oiHigh
        #oi_day_low to oiLow
    '''
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
    
    #If run as standalone, ticker will pickup close values from dasConfig.json
    DAS_Ticker(marketCloseHour,marketCloseMinute)
    #DAS_Ticker(12,44)
