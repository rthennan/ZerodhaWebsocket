# -*- coding: utf-8 -*-
"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Dumps the tables from the 'Daily' databases to a backup database.
1. Maintaines efficiency of replace statements in daily tables as they would have one day's data at most 
2. Facilitates regular clean up
3. Helps idenfy small tables in Nifty500, resulting from symbol changes and delisting 
4. Backup tables can be migrated / downloaded even if ticker is running

Checks and reports if any of the tables in lookupTables_Nifty500.csv are empty at the end of the day.
    This indicates that the corresponding symbol has potentially changed or has been delisted
Creates main databases {nifty500DBName}, {niftyOptionsDBName} and {bankNiftyOptionsDBName} . (No _daily suffix)
Copies all tables from the _daily databases to their corresponding main database and drops the tables in the _daily DBs
Reports about backup failures.
End of DAS_main
Returns True if success. Else False.
"""

from datetime import datetime as dt, date
import MySQLdb
from DAS_gmailer import DAS_mailer
from DAS_attachmentMailer import sendMailAttach 
from os import path, makedirs
import pandas as pd
import json
import traceback
from DAS_errorLogger import DAS_errorLogger
import numpy as np
from sqlalchemy import create_engine
import concurrent.futures

configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)
recipientEmailAddress = dasConfig['destinationEmailAddress']
#Generate a list if multiple recipients mentioned
recipientEmailAddress = recipientEmailAddress.split(',')
senderEmailAddress = dasConfig['senderEmailAddress']
senderEmailPass = dasConfig['senderEmailPass']
mysqlHost = dasConfig['mysqlHost']
mysqlUser = dasConfig['mysqlUser']
mysqlPass = dasConfig['mysqlPass']
mysqlPort = dasConfig['mysqlPort']

nifty500DBName = dasConfig['nifty500DBName']
niftyOptionsDBName = dasConfig['niftyOptionsDBName']
bankNiftyOptionsDBName = dasConfig['bankNiftyOptionsDBName']

backupWorkerCount = dasConfig['backupWorkerCount']

dailyTableName = 'dailytable'

#Preapare Lookup tables and lists
lookupDir = 'lookupTables'
#Identify Only Nifty and BankNifty as they have a different table structure and hence different SQL stmnt
indexTokens = pd.read_csv(path.join(lookupDir,'indexTokenList.csv'))['instrument_token'].values.tolist()  
   
#Nifty500 Tokens and Token Table (Lookup => instrument_token:TableName)
#Includes Nifty 500, Nifty, BankNifty and their Futures
nifty500Tokens = pd.read_csv(path.join(lookupDir,'nifty500TokenList.csv'))['instrument_token'].values.tolist()
nifty500TokenTableDict = np.load(path.join(lookupDir,'nifty500TokenTableDict.npy'),allow_pickle=True).item() 
nifty500TokenSymbolDict = np.load(path.join(lookupDir,'nifty500TokenSymbolDict.npy'),allow_pickle=True).item() 
   

#Nifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
niftyOptionTokens = pd.read_csv(path.join(lookupDir,'niftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
niftyOptionsTokenTableDict = np.load(path.join(lookupDir,'niftyOptionsTokenTableDict.npy'),allow_pickle=True).item() 

#BankNifty Options Tokens and Token Table(Lookup => instrument_token:TableName)
bankNiftyOptionTokens = pd.read_csv(path.join(lookupDir,'bankNiftyOptionsTokenList.csv'))['instrument_token'].values.tolist()
bankNiftyOptionsTokenTableDict = np.load(path.join(lookupDir,'bankNiftyOptionsTokenTableDict.npy'),allow_pickle=True).item() 

#Combine all token lists
fullTokenList = indexTokens+nifty500Tokens+niftyOptionTokens+bankNiftyOptionTokens

#Combine all three token:table dictionairies
mainTokenTableDict = {}
mainTokenTableDict.update(nifty500TokenTableDict)
mainTokenTableDict.update(niftyOptionsTokenTableDict)
mainTokenTableDict.update(bankNiftyOptionsTokenTableDict)


#Combine all three token:symbol dictionairies
mainTokenSymbolDict = {}
mainTokenSymbolDict.update(nifty500TokenSymbolDict)
mainTokenSymbolDict.update(niftyOptionsTokenTableDict) #Symbol and tableName are same for nifty options
mainTokenSymbolDict.update(bankNiftyOptionsTokenTableDict) #Symbol and tableName are same for BankNifty options 

#Creating a lookup dictionairy for instrument_token:DBName
tokenToDbNameDict = {token: nifty500DBName for token in nifty500Tokens}
tokenToDbNameDict.update({token: niftyOptionsDBName for token in niftyOptionTokens})
tokenToDbNameDict.update({token: bankNiftyOptionsDBName for token in bankNiftyOptionTokens})  

def dailyBackupLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_dailyBackup_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

def dailyBackupLogNoPrint(txt):
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_dailyBackup_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)        
    
def findSymbolsForTable(tableName,symbolTableDF):
    # Filter the DataFrame where 'TableName' matches tbName and select the 'Symbol' column
    matchingSymbols = symbolTableDF[symbolTableDF['TableName'] == tableName]['Symbol']
    # Convert matching symbols to list and join them with commas
    matchingSymbols = matchingSymbols.tolist()
    return ','.join(matchingSymbols)

def findNifty500blankTables():
    #Identify tablenames for which no data was received.
    #Indicates that the correponsing symbol is potentially invalid - Symbol changed or delisted
    lookupDirectory = 'lookupTables'
    n500instrumentLookupFile = 'lookupTables_Nifty500.csv'
    n500InstrumentFilePath = path.join(lookupDirectory,n500instrumentLookupFile)
    n500InstrumentSymbolsTables = pd.read_csv(n500InstrumentFilePath)
    n500InstrumentTables = sorted(n500InstrumentSymbolsTables['TableName'].values.tolist())
      
    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
    c = conn.cursor()
    
    c.execute(f"SELECT DISTINCT(tablename) FROM {nifty500DBName}.{dailyTableName}")
    tableNamesInTicks = list([item[0] for item in c.fetchall()])
    noDataTables = sorted(list(set([item for item in n500InstrumentTables if item not in tableNamesInTicks])))
    if len(noDataTables) == 0:
        blanknifty500TablesDF = pd.DataFrame()
    if len(noDataTables) > 0:
        #Found Blank Tables
        blanknifty500TablesDF = pd.DataFrame(noDataTables, columns=['TableName'])
        #Find matching SYmbol(s)
        #If multiple symbols are mapped to one table, find all the symbols.
        #A known example would be -BE (Book Entry) instruments where symbols with and without BE mapped to the same table name
        #A simple lookup/ dictionary call won't do
        # call findSymbolsForTable for each row in blanknifty500TablesDF
        blanknifty500TablesDF['TradingSymbols'] = blanknifty500TablesDF['TableName'].apply(lambda x: findSymbolsForTable(x, n500InstrumentSymbolsTables))
    c.close()
    conn.close()
    return blanknifty500TablesDF

def DAS_backupOneInstrument(instToken):
    conn3 = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
    c3 = conn3.cursor()
    #Get Tablename and DBName
    tableName = mainTokenTableDict.get(instToken) 
    dbName = tokenToDbNameDict.get(instToken)
    tradingsymbol = mainTokenSymbolDict.get(instToken)
    #Insert entry into faileBackupTables
    #Doing this now and removing later on success.
    #This way, if the backup fails mid-way for some reason adn DB cursor becomes unusable,we'll still know that the backup failed
    c3.execute(f"INSERT INTO {nifty500DBName}.failedbackuptables VALUES (%s,%s,%s)",[instToken,tradingsymbol,tableName])
    if instToken in fullTokenList:
        try:
            msg = f'Started backing up InstToken {instToken} into {dbName}.`{tableName}`.'
            dailyBackupLogger(msg)
            if instToken in indexTokens :
                #Create Table in the appropriate DB
                #Copy all rows for that instrument token from daily table to main table
                c3.execute(f"CREATE TABLE IF NOT EXISTS {dbName}.`{tableName}` (timestamp DATETIME UNIQUE,price decimal(12,2))")
                c3.execute(f'''
                          REPLACE INTO {dbName}.`{tableName}` 
                          SELECT timestamp,price FROM {nifty500DBName}.{dailyTableName}
                          WHERE instrument_token={instToken}
                          ''')
            else:
                #Create Table in the appropriate DB
                #Copy all rows for that instrument token from daily table to main table
                c3.execute(f'''
                          CREATE TABLE IF NOT EXISTS {dbName}.`{tableName}` 
                        	(timestamp DATETIME UNIQUE,price DECIMAL(19,2), qty INT UNSIGNED, 
                          avgPrice DECIMAL(19,2), volume BIGINT,
                          bQty INT UNSIGNED, sQty INT UNSIGNED, 
                          open DECIMAL(19,2), high DECIMAL(19,2), low DECIMAL(19,2), close DECIMAL(19,2),
                        	changeper DECIMAL(60,10), lastTradeTime DATETIME, oi INT, oiHigh INT, oiLow INT, 
                        	bq0 INT UNSIGNED, bp0 DECIMAL(19,2), bo0 INT UNSIGNED,
                        	bq1 INT UNSIGNED, bp1 DECIMAL(19,2), bo1 INT UNSIGNED,
                        	bq2 INT UNSIGNED, bp2 DECIMAL(19,2), bo2 INT UNSIGNED,
                        	bq3 INT UNSIGNED, bp3 DECIMAL(19,2), bo3 INT UNSIGNED,
                        	bq4 INT UNSIGNED, bp4 DECIMAL(19,2), bo4 INT UNSIGNED,
                        	sq0 INT UNSIGNED, sp0 DECIMAL(19,2), so0 INT UNSIGNED,
                        	sq1 INT UNSIGNED, sp1 DECIMAL(19,2), so1 INT UNSIGNED,
                        	sq2 INT UNSIGNED, sp2 DECIMAL(19,2), so2 INT UNSIGNED,
                        	sq3 INT UNSIGNED, sp3 DECIMAL(19,2), so3 INT UNSIGNED,
                        	sq4 INT UNSIGNED, sp4 DECIMAL(19,2), so4 INT UNSIGNED
                            )
                         '''
                          )
                #Copy data for instToken from dailyTable to individual table in the main DB
                c3.execute(f''' 
                          REPLACE INTO {dbName}.`{tableName}`
                          SELECT 
                          timestamp, price, qty, avgPrice, volume,
                          bQty,sQty, open, high, low, close, 
                          changeper, lastTradeTime,  oi, oiHigh, oiLow,
                          bq0, bp0, bo0, bq1, bp1, bo1,
                          bq2, bp2, bo2, bq3, bp3, bo3,
                          bq4, bp4, bo4, 
                          sq0, sp0, so0, sq1, sp1, so1,
                          sq2, sp2, so2, sq3, sp3, so3,
                          sq4, sp4, so4
                          FROM {nifty500DBName}.{dailyTableName}
                          WHERE instrument_token={instToken}   
                          ''')
            #msg = f'InstToken {instToken} backed up into {dbName}.`{tableName}.'
            #dailyBackupLogNoPrint(msg)
            c3.execute(f"DELETE FROM {nifty500DBName}.failedbackuptables WHERE instrument_token={instToken}")
            conn3.commit()
            msg = f'Finished backing up InstToken {instToken} into {dbName}.`{tableName}`.'
            dailyBackupLogger(msg)
        except Exception as e:
            msg = f'DAS_dailyBackup - Exception while copying instToken {instToken} data to {dbName}.`{tableName} : {e} . Traceback : {traceback.format_exc()}'
            dailyBackupLogger(msg)
            DAS_errorLogger('DAS_dailyBackup - '+msg)
        finally: 
            c3.close()
            conn3.close()
    else:
        msg = f'Found data for unsbscribed instrument_token {instToken}'
        dailyBackupLogger(msg)
        DAS_errorLogger('DAS_dailyBackup - '+msg)

def DAS_dailyBackup():
    try:
        #Find instrumentTokens in subscription list with no data received.
        blankTablesFound = False
        blankNifty500Tables = findNifty500blankTables()
        if len(blankNifty500Tables)>0:
            blankTablesFound = True
            #Store the list locally for future reference
            blankTablesDir = 'blankNifty500Tables'
            if not path.exists(blankTablesDir):
                makedirs(blankTablesDir)
            todayBlankTablesName=f'blankNifty500Instruments_{str(date.today())}.csv'
            blankTablesLocPath = path.join(blankTablesDir,todayBlankTablesName)
            blankNifty500Tables.to_csv(blankTablesLocPath,index=False)
            blankTableMsg = f'No ticks received for {len(blankNifty500Tables)} symbols provided in lookupTables_Nifty500.csv.\nStored the list as {todayBlankTablesName}'
            dailyBackupLogger(blankTableMsg)
            
        #Create Databases and Tables
        #Find unique databaseNames.
        #This is to allow backups irrespective of whether 
        #the same name or different names have been used for the three databases
        dbNames = [nifty500DBName,niftyOptionsDBName,bankNiftyOptionsDBName]
        #Sorted unique list
        dbNames = sorted(list(set(dbNames)))
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
        c = conn.cursor()
        #Create databases
        for dbName in dbNames:
            c.execute(f"CREATE DATABASE IF NOT EXISTS {dbName}")
        
        #Find insturment_tokens from the daily table.
        c.execute(f"SELECT DISTINCT(instrument_token) FROM {nifty500DBName}.{dailyTableName}")
        instrumentTokensToStore = list([item[0] for item in c.fetchall()])
        #Find rowCount 
        c.execute(f"SELECT COUNT(*) FROM {nifty500DBName}.{dailyTableName}")
        dailyTableRowCount = int(c.fetchone()[0])            
    
        msg = f'''
            DAS_dailyBackup is about to distribute {dailyTableRowCount} rows for {len(instrumentTokensToStore)} instruments from the daily table into main DBs and tables.
            This is going to take some time
            '''
        dailyBackupLogger(msg)
        
        #Create TABLE to record list of instrument_tokens that failed backup.
        #Using DB, as backup is multi-threaded and variable sharing between threads is cumbersome
        c.execute(f'''
                  CREATE TABLE IF NOT EXISTS 
                  {nifty500DBName}.failedbackuptables 
                  (instrument_token BIGINT(20),
                   tradingsymbol VARCHAR(100),
                   tablename VARCHAR(100)
                   )                  
                  ''')       
        
        #Calling DAS_backupOneInstrument for instrumentTokensToStore
        msg = f'Calling DAS_backupOneInstrument for {len(instrumentTokensToStore)} instrument tokens with {backupWorkerCount} concurrent workers'
        dailyBackupLogger(msg)
        with concurrent.futures.ThreadPoolExecutor(max_workers=backupWorkerCount) as executor:
            executor.map(DAS_backupOneInstrument, instrumentTokensToStore)
        
        msg = 'DAS_backupOneInstrument completed. Looking for failed backups'
        dailyBackupLogger(msg)
        
        #Check If backup failed for any token
        engine = create_engine(f'mysql+mysqldb://{mysqlUser}:{mysqlPass}@{mysqlHost}:{mysqlPort}/{nifty500DBName}')
        bakupFailedTokens = pd.read_sql(f"SELECT * FROM {nifty500DBName}.failedbackuptables", engine)
        
        #Drop failedbackuptables
        c.execute(f"DROP TABLE {nifty500DBName}.failedbackuptables")
        conn.commit()
        
        if len(bakupFailedTokens) > 0:
            #Closing the connection and cursor object.
            c.close()
            conn.close()
            #Store failed tables for future reference 
            backUpFailsDir = 'backupFailedTables'
            if not path.exists(backUpFailsDir):
                makedirs(backUpFailsDir)
            todaybackupFailsName=f'backupsFailed_{str(date.today())}.csv'
            failedTablesLocPath = path.join(backUpFailsDir,todaybackupFailsName)
            bakupFailedTokens.to_csv(failedTablesLocPath,index=False)
            failTablesMsg = f'DAS_dailybackup failed for {len(bakupFailedTokens)} instrument_token(s).\ndailytable left untouched.\nStored the list as {todaybackupFailsName}'
            failTableString = '\n'.join(f"{item}, {mainTokenSymbolDict.get(item)}" for item in bakupFailedTokens['instrument_token'].tolist())
            dailyBackupLogger(failTablesMsg)
            dailyBackupLogger(failTableString)
            DAS_errorLogger('DAS_dailyBackup - '+failTablesMsg)
            DAS_errorLogger(failTableString)
            if blankTablesFound:
                blankTableMsg = f'No ticks received for {len(blankNifty500Tables)} symbols provided in lookupTables_Nifty500.csv . List attached\n'
                #sendMailAttach(subject,body,attachfilePath)
                sendMailAttach('DAS_dailybackup failed and instrumentTokens with no data found. Check Logs for more details',
                               blankTableMsg+failTablesMsg+failTableString,
                               blankTablesLocPath) 
                dailyBackupLogger('Blank Table List mailed')
                dailyBackupLogger('DAS Dailybackup completed')
                
            else:
                DAS_mailer(failTablesMsg,failTablesMsg+failTableString)
            return False
        #Backup succeeded for all tables;
        else:
            #Drop dailytable
            c.execute(f"DROP TABLE {nifty500DBName}.{dailyTableName}")
            dailyBackupLogger('Backup successful for all instrument tokens.Daily Table Dropped.')
            #Committing and Closing the connection and cursor object.
            conn.commit()
            c.close()
            conn.close()
            if blankTablesFound:
                blankTableMsg = f'No ticks received for {len(blankNifty500Tables)} symbols provided in lookupTables_Nifty500.csv . List attached\n'
                #sendMailAttach(subject,body,attachfilePath)
                sendMailAttach('DAS - Done for the day. All activities completed successfully. instrumentTokens with no data found. List attached',
                               'DAS - DAS_dailybackup completed. '+ blankTableMsg,
                               blankTablesLocPath) 
                dailyBackupLogger('Blank Table List mailed')
                dailyBackupLogger('DAS Dailybackup completed')
            else:
                msg = 'DAS - Done for the day. All activities completed successfully. No Blank Tables found'
                dailyBackupLogger(msg)
                #Mailing all good as this is the last operation in DAS Main
                DAS_mailer(msg,'DAS - DAS_dailybackup completed. '+msg)
                dailyBackupLogger('DAS Dailybackup completed')
            return True        
        #Mail notifying success and failure here as this is the last activity
        #Success will inlucde blank tables if found
        #Failure will be returned to DAS_main but it will only be logged threre. No notify.
        #This avoids duplicate notifications
        #Catch all False indicating potential failures
        return False
        
    except Exception as e:
        msg = f'Exception in DAS_dailyBackup : {e} . Traceback : {traceback.format_exc()}'
        dailyBackupLogger(msg)
        DAS_mailer(msg,'DAS - DAS_dailybackup failed with exception. '+msg)
        DAS_errorLogger('DAS_dailyBackup - '+msg)
        return False          
        
if __name__ == '__main__':
    DAS_dailyBackup() 