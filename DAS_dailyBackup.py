# -*- coding: utf-8 -*-
"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan

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

nifty500_daily_DBName = nifty500DBName+'_daily'
niftyOptions_daily_DBName = niftyOptionsDBName+'_daily'
bankNiftyOptions_daily_DBName = bankNiftyOptionsDBName+'_daily'

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

def findNifty500blankTables():
    #Identify tables from {nifty500_daily_DBName}_daily where row count is zero
    #Indicates that the correponsing symbol is potentially invalid
    #Symbol changes or delisting
    blanknifty500TablesDF = pd.DataFrame(columns=['tradingSymbol','TableName'])
    lookupDirectory = 'lookupTables'
    n500instrumentLookupFile = 'lookupTables_Nifty500.csv'
    n500InstrumentFilePath = path.join(lookupDirectory,n500instrumentLookupFile)
    n500InstrumentSymbolsTables = pd.read_csv(n500InstrumentFilePath)
    n500InstrumentTables = sorted(n500InstrumentSymbolsTables['TableName'].values.tolist())
    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
    c = conn.cursor()
    #Based on dasConfig.json, the same DB could be used for storing Nifty500 and Options as well.
    #Hence using the lookup table to find blank Tables
    for instrumentTable in n500InstrumentTables:
        c.execute(f"SELECT COUNT(*) FROM {nifty500_daily_DBName}.`{instrumentTable}`")
        tbRowCount=c.fetchone()[0]
        if tbRowCount == 0:
            # Find the corresponding Symbol for the given instrumentTable
            tradingSymbol = n500InstrumentSymbolsTables.loc[n500InstrumentSymbolsTables['TableName'] == instrumentTable, 'Symbol'].values[0]
            # Create a new DataFrame for this row
            newRow = pd.DataFrame({'tradingSymbol': [tradingSymbol],'TableName': [instrumentTable]})
            # Use pandas.concat to append instrumentTable as TableName and found Symbol as tradingSymbol to blankn500TablesDF
            blanknifty500TablesDF = pd.concat([blanknifty500TablesDF, newRow], ignore_index=True)
    #Storing and mailing blank Tables in the main loop - DAS_dailyBackup to avoid multiple emails
    #If empty tables are found, it will be reported in the backup completion email
    c.close()
    conn.close()
    return blanknifty500TablesDF


def DAS_dailyBackup():
    bakupFailedTables = []
    try:
        #Find blank Nifty 500 tables.
        blankTablesFound = False
        blankNifty500Tables = findNifty500blankTables()
        if len(blankNifty500Tables)>0:
            blankTablesFound = True
            #Store the list locally for future reference
            blankTablesDir = 'blankNifty500Tables'
            if not path.exists(blankTablesDir):
                makedirs(blankTablesDir)
            todayTableName=f'blankNifty500Tables_{str(date.today())}.csv'
            blankTablesLocPath = path.join(blankTablesDir,todayTableName)
            blankNifty500Tables.to_csv(blankTablesLocPath,index=False)
            blankTableMsg = f'Found {len(blankNifty500Tables)} blankTables for Nifty500.\nStored the list as {todayTableName}'
            dailyBackupLogger(blankTableMsg)
            
        #Find unique databaseNames.
        #This is to allow backups irrespective of whether 
        #the same name or different names have been used for the three databases
        dBNames = [nifty500DBName,niftyOptionsDBName,bankNiftyOptionsDBName]
        #Sorted unique list
        dBNames = sorted(list(set(dBNames)))
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
        c = conn.cursor()
        
        #For each database:
            #For each table:
                #Create copy (Replace INTO) of table from daily database to main database
                    #Drop table from daily database after copy

        for dbName in dBNames:
            #Create main database if necessary
            c.execute(f"CREATE DATABASE IF NOT EXISTS {dbName}")
            #Get Table Names
            msg = f'Backing up Tables from {dbName}_daily to {dbName}'
            dailyBackupLogger(msg)
            c.execute(f"SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = '{dbName}_daily'")
            instrumentTables = list([item[0] for item in c.fetchall()])
            
            for instTable in instrumentTables:
                #Using a separate conenction object for each Backup operation
                #As failure at times might leave the connection object in a borked unsuable state
                #This approach is simpler, compared to Global variable /recreating the object on exception only
                conn2 = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
                c2 = conn2.cursor()
                try:
                    # Try executing the CREATE TABLE and REPLACE operations
                    c2.execute(f'CREATE TABLE IF NOT EXISTS {dbName}.`{instTable}` LIKE {dbName}_daily.`{instTable}`')
                    c2.execute(f'REPLACE INTO {dbName}.`{instTable}` SELECT * FROM {dbName}_daily.`{instTable}`')
                    # If both operations succeed, then DROP the table
                    msg = f'Table {dbName}_daily.{instTable} backed up. Dropping it'
                    dailyBackupLogNoPrint(msg)
                    c2.execute(f'DROP TABLE {dbName}_daily.`{instTable}`')
                except Exception as e:
                    bakupFailedTables.append(f'{dbName}_daily.{instTable}')
                    msg = f'Error while backing up and dropping Table {dbName}_daily.{instTable}. Exception: {e}. Traceback : {traceback.format_exc()}'
                    dailyBackupLogger(msg)
                    DAS_errorLogger('DAS_dailyBackup - '+msg)
                finally:
                    c2.close()
                    conn2.close()
            msg = f'Backup Operations completed for {dbName}_daily'
            dailyBackupLogger(msg)
            
        c.close()
        conn.close()
        #If backup failed for one or more tables
        if len(bakupFailedTables) > 0:
            failTablesMsg = f'DAS_dailybackup failed for {len(bakupFailedTables)} table(s)'
            failTableString = '\n'.join(bakupFailedTables)
            dailyBackupLogger(failTablesMsg)
            dailyBackupLogger(failTableString)
            DAS_errorLogger('DAS_dailyBackup - '+failTablesMsg)
            DAS_errorLogger(failTableString)
            if blankTablesFound:
                blankTableMsg = f'{len(blankNifty500Tables)} blank table(s) found in the Nifty500 DB {nifty500_daily_DBName}. List attached\n'
                #sendMailAttach(subject,body,attachfilePath)
                sendMailAttach('DAS_dailybackup failed and blank Nifty-500 Tables found. Check Logs for more details',
                               blankTableMsg+failTablesMsg+failTableString,
                               blankTablesLocPath) 
                dailyBackupLogger('Blank Table List mailed')
                
            else:
                DAS_mailer(failTablesMsg,failTablesMsg+failTableString)
            return False
        else:
            if blankTablesFound:
                blankTableMsg = f'{len(blankNifty500Tables)} blank tables found in the Nifty500 DB {nifty500_daily_DBName}. List attached\n'
                #sendMailAttach(subject,body,attachfilePath)
                sendMailAttach('DAS - Done for the day. All activities completed successfully. Blank Nifty-500 Tables found. List attached',
                               'DAS - DAS_dailybackup completed. '+ blankTableMsg,
                               blankTablesLocPath) 
                dailyBackupLogger('Blank Table List mailed')
            else:
                msg = 'DAS - Done for the day. All activities completed successfully. No Blank Tables found'
                dailyBackupLogger(msg)
                #Mailing all good as this is the last operation in DAS Main
                DAS_mailer(msg,'DAS - DAS_dailybackup completed. '+msg)
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