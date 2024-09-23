# -*- coding: utf-8 -*-
"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Can be Run standalone

Will Fetch Nifty 500 list from https://archives.nseindia.com/content/indices/ind_nifty500list.csv
If local file doesn't exist, 
    - Will create a new 'lookup file with the instrument symbols
    - Add NIFTY, BANKNIFTY and their current month futures to it
    - Create corresponding DB friendly table names
If Local file exists:
    - Cross check symbols there with the symbols in the local file
    - Will add new symbols and create corresponding DB friendly table names
    - Will NOT REMOVE any existing symbols in the file.
    - Only exceptions are NIFTYFUT and BANKNIFTYFUT as the symbol changes every month
Advantages:
    - Removes the need for regular maintenace when Nifty500 is updated
    - Automatically picks up new symbols that result from symbol changes
    - Log such changes to NIFTY500_symbolsAdded.log
Disadvantage:
    - Symbol changes will not be recognized.
        - Example:
            Amara Raja Energy & Mobility Ltd.Changed from AMARAJABAT (Table Name AMARAJABAT) to ARE&M (Table Name ARE_M)
            in September 2023.
            This would result in a new entry added to the list for ARE&M - ARE_M
            While this ensures that the new symbol's data is captured,
                - Splits the data into two tables 
                - Leaves the old table hanging
            Hence when you read data, you would have to Union  AMARAJABAT and ARE_M to get the full picture.
     - The small tables report sent at the end of every day and nifty500_SymbolsChanged.log can be used to manage this situation
     - Delisted stocks won't be removed from the existing lookupTables_Nifty500.csv file
ChangeLog for symbols identified manually:
    - Amara Raja Energy & Mobility Ltd.Changed from AMARAJABAT (Table Name AMARAJABAT) to ARE&M (Table Name ARE_M)
    in September 2023.
    - Kennametal India Limited (KENNAET) was removed from the NSE on October 26, 2023
    - TATACOFFEE delisted - https://tradingqna.com/t/everything-you-need-to-know-about-merger-of-tata-coffee-with-tata-consumer-products/158981
    - WELSPUNIND to WELSPUNLIV on 14 Dec 2023
    - ADANITRANS to ADANIENSOL with effect from August 24, 2023
    - MFL changed to EPIGRAL  with effect from September 11, 2023

ChangeLog:
2024-09-23:
    Nifty 500 list URL changed from https://archives.nseindia.com/content/indices/ind_nifty500list.csv to https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv
    And NSE seems to have started blocking programmatic access.
    Hence mimicking a user-agent (generateRandomUserAgent) and extracting CSV from the response text.
    

"""

import pandas as pd
from datetime import datetime as dt, timedelta, date
import shutil
from os import path, makedirs
import sys
from time import sleep
from DAS_gmailer import DAS_mailer
import traceback
from DAS_errorLogger import DAS_errorLogger
from io import StringIO
import requests
import random

numbOfRetries = 5

lookUpFilesDir = 'lookupTables'
currentLookUpFileName = 'lookupTables_Nifty500.csv'
currentLookupTablePath = path.join(lookUpFilesDir,currentLookUpFileName)
n500url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


def nifty500UpdateMainlogger(txt):
    print(dt.now(),'nifty500UpdateRun',txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'DAS_nifty500UpdateRun_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)
        
def nifty500UpdateChangelogger(txt):
    print(dt.now(),'nifty500_SymbolsChanged', txt)
    logFile = 'nifty500_SymbolsChanged.log'
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)      


def generateRandomUserAgent():
    platforms = [
        'Windows NT 10.0; Win64; x64',
        'Macintosh; Intel Mac OS X 10_15_7',
        'X11; Linux x86_64',
        'iPhone; CPU iPhone OS 14_0 like Mac OS X',
        'Android 10; Mobile;'
    ]
    
    browsers = [
        ('Chrome', ['91.0.4472.124', '92.0.4515.159', '93.0.4577.82']),
        ('Firefox', ['89.0', '90.0', '91.0']),
        ('Safari', ['14.0.1', '13.1.2', '12.1.2']),
        ('Edge', ['91.0.864.59', '92.0.902.55'])
    ]
    
    # Randomly select a platform and browser
    platform = random.choice(platforms)
    browser, versions = random.choice(browsers)
    version = random.choice(versions)
    
    # Construct the User-Agent string based on the platform and browser
    if browser == 'Safari':
        user_agent = f'Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15'
    elif browser == 'Chrome':
        user_agent = f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36'
    elif browser == 'Firefox':
        user_agent = f'Mozilla/5.0 ({platform}; rv:{version}) Gecko/20100101 Firefox/{version}'
    elif browser == 'Edge':
        user_agent = f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/{version}'
    
    msg = f'User agent for the day:\n {user_agent}'
    nifty500UpdateMainlogger(msg)
    return user_agent




#Used for NIFTYFUT
def lastThursday(inputDate):   
    # Convert string to datetime
    #inputDate = dt.strptime(dateString, '%Y-%m-%d')    
    # Last day of the input month
    lastDayofTheMonth = (date(inputDate.year, inputDate.month + 1, 1) - timedelta(days=1)).day
    # Date of the last day of the input month
    lastDate = date(inputDate.year, inputDate.month, lastDayofTheMonth)    
    # Find the last Thursday
    if lastDate.weekday() == 3:
        lastThursday = lastDate
    else:
        lastThursday = lastDate - timedelta(days=(lastDate.weekday() - 3) % 7)
    return lastThursday

#Used for BANKNIFTYFUT
def lastWednesday(inputDate):
    # Last day of the input month
    lastDayofTheMonth = (date(inputDate.year, inputDate.month + 1, 1) - timedelta(days=1)).day
    # Date of the last day of the input month
    lastDate = date(inputDate.year, inputDate.month, lastDayofTheMonth)
    # Find the last Wednesday
    if lastDate.weekday() == 2:
        lastWednesday = lastDate
    else:
        lastWednesday = lastDate - timedelta(days=(lastDate.weekday() - 2) % 7)
    return lastWednesday


def getCurrentFuture(indexName):
    #currentDate
    indexName = indexName.upper()
    todayDate = date.today()
    if indexName == 'NIFTY':
        thisMonthExpiryDate = lastThursday(todayDate)
    elif indexName == 'BANKNIFTY':
        thisMonthExpiryDate = lastWednesday(todayDate)
    #If today is less than or equal to expiry date, use this month expiry.
    if todayDate <= thisMonthExpiryDate:
        #current month future
        thisMonth = todayDate.strftime("%b").upper()
        thisYear= todayDate.year  
        thisMonthFutFormat = str(thisYear)[-2:] + thisMonth + 'FUT'
        return indexName+thisMonthFutFormat

    else:
        #Incrementing the date by 15 days to get the next Future's Month and year
        #Might be able to get away with 6 or 7 days. Doing 15 as a safe measure
        nextMonthDate = todayDate + timedelta(days=15)
        nextMonth = nextMonthDate.strftime("%b").upper()
        nextMonthYear= nextMonthDate.year  
        nextMonthFutFormat = str(nextMonthYear)[-2:] + nextMonth + 'FUT'
        return indexName+nextMonthFutFormat

def replaceSpecial(intext):
    #Remove '-BE' if found at the end of the symbolName
    #Subscribe to the BE symbols, yes.
    #But store tick data in table name without the BE flag
    #This way, if/when the BE flag gets removed, the data will still be in the same table
    if intext[-3:] == '-BE':
        intext = intext[:-3]
    #Replace non table name friendly special characters with _
    return intext.replace('-BE','').replace('-', '_').replace('&', '_')

def getNifty500SymbolList():    
    '''
    If Series is of type 'BE' (Book Entry), add '-BE' to the end of the symbol
    This seems to be the valid symbol for Zerodha.
    Examples: 
        TATAINVEST becomes TATAINVEST-BE
        ALOKINDS becomes ALOKINDS-BE        
    '''
    #Retry 5 times
    for attempt in range(1,numbOfRetries+1):
    
        try:    
            response = requests.get(n500url, headers={'User-Agent': generateRandomUserAgent()})
            csv_data = StringIO(response.text)
            nifty500FromNSE = pd.read_csv(csv_data)
            nifty500FromNSE.loc[nifty500FromNSE['Series'] == 'BE', 'Symbol'] += '-BE'
            return nifty500FromNSE['Symbol'].tolist()   
        except Exception as e:
            msg = f'getNifty500SymbolList Failed. Attempt No :{attempt} . Exception-> {e} Traceback : {traceback.format_exc()}.\nWill retry after 30 seconds'
            nifty500UpdateMainlogger(msg)
            DAS_errorLogger('nifty500Updater - '+msg)
            sleep(30)
        else:
            break

    else:
        msg = f'getNifty500SymbolList - Failed After {numbOfRetries} attempts. Exiting Execution'
        nifty500UpdateMainlogger(msg)
        DAS_errorLogger('nifty500Updater - '+msg)
        DAS_mailer('DAS Nifty 500 - getNifty500SymbolList Failed. Exiting',msg)   
        sys.exit()
    

def createSymbolTableNameList():
    msg = f'{path.join(lookUpFilesDir,currentLookUpFileName)} not found. Creating a new lookupTable'
    nifty500UpdateMainlogger(msg)
    nifty500UpdateChangelogger(msg)
    #create a new dataframe with Symbol and TableName Columns
    lookupTable = pd.DataFrame(columns=['Symbol', 'TableName'])
    
    #Add Nifty and BankNifty Index
    indexesToAdd = [{'Symbol': 'NIFTY 50', 'TableName': 'NIFTY'},
                    {'Symbol': 'NIFTY BANK', 'TableName': 'BANKNIFTY'}]
    
    # Convert indexesToAdd to a DataFrame before concatenation if it's not already a DataFrame
    indexesToAdd_df = pd.DataFrame(indexesToAdd)
    
    # Add indexes to lookupTable
    lookupTable = pd.concat([lookupTable, indexesToAdd_df], ignore_index=True)
    
    #Add Nifty and BankNifty Futures
    niftyCurrentFuture = getCurrentFuture('NIFTY')
    bankNiftyCurrentFuture = getCurrentFuture('BANKNIFTY')
    futuresToAdd = [{'Symbol': niftyCurrentFuture, 'TableName': 'NIFTYFUT'},
                    {'Symbol': bankNiftyCurrentFuture, 'TableName': 'BANKNIFTYFUT'}]
    
    futuresToAdd_df = pd.DataFrame(futuresToAdd)
    #Add Futures to the lookup table
    lookupTable = pd.concat([lookupTable, futuresToAdd_df], ignore_index=True)
    
    #Get Nifty 500 list 
    nifty500SymbolList = getNifty500SymbolList()
    nifty500SymbolsDF = pd.DataFrame({'Symbol': sorted(nifty500SymbolList)})
    #Create a 'TableName' column
    #TableName will be almost the same as Symbols, 
    #but replaces special characters with _ to make it work with MySQL/ MariaDB
    nifty500SymbolsDF['TableName'] = nifty500SymbolsDF['Symbol'].apply(lambda x: replaceSpecial(x))

    #Add nifty 500 to the lookup table     
    lookupTable = pd.concat([lookupTable, nifty500SymbolsDF], ignore_index=True)
    
    #Arrange Alphabetically
    lookupTable = lookupTable.sort_values(by='Symbol')
    
    #Save to File
    if not path.exists(lookUpFilesDir):
        makedirs(lookUpFilesDir)
    
    newLookupTableFilePath = path.join(lookUpFilesDir,currentLookUpFileName)
    lookupTable.to_csv(newLookupTableFilePath, index=False)
    msg = 'lookup Table lookupTables_Nifty500.csv not found. Created it '
    nifty500UpdateChangelogger(msg)
    #mail(destinationEmailAddress, 'DAS Main - Access token Failed.',msg)     
    DAS_mailer('DAS - lookupTables_Nifty500 created',msg)
    
def updateSymbolTableNameList():
    lookupTableChanged = False
    changesMade = ''
    lookupTable = pd.read_csv(path.join(lookUpFilesDir,currentLookUpFileName))
    
    #Checking if nifty500 list has new symbols
    existingSymbols = lookupTable['Symbol'].tolist()
    n500currentSymbols = getNifty500SymbolList()
    missingSymbols = list(set(n500currentSymbols) - set(existingSymbols))
    if len(missingSymbols)>0:
        symbolsToAdd = pd.DataFrame({'Symbol': sorted(missingSymbols)})
        #Create new Table Names for new symbols, replacing special charachters
        symbolsToAdd['TableName'] = symbolsToAdd['Symbol'].apply(lambda x: replaceSpecial(x))
        lookupTable = pd.concat([lookupTable, symbolsToAdd], ignore_index=True)   
        msg = f'Found {len(missingSymbols)} new symbol(s) in Nifty500 list.'
        nifty500UpdateChangelogger(msg)
        nifty500UpdateMainlogger(msg)
        changesMade = changesMade+ '\nSymbol  TableName'
        for row in range(len(symbolsToAdd)):
            changesMade = f"{changesMade}\n{symbolsToAdd['Symbol'].iloc[row]}  {symbolsToAdd['TableName'].iloc[row]}  "        
        lookupTableChanged = True
        
    #Check if NIFTYFUT and BANKNIFTYFUT have to be updated.
    currentNiftyFut = getCurrentFuture('NIFTY')
    currentBankNiftyFut = getCurrentFuture('BANKNIFTY')
    
    #Find the existing NIFTYFUT symbol in lookupTable and replace it if necessary
    niftyFutInLookup = lookupTable[lookupTable['TableName'] == 'NIFTYFUT']['Symbol'].iloc[0]
    if niftyFutInLookup != currentNiftyFut:
        #NiftyFut Symbol needs to be updated
        lookupTable.loc[lookupTable['TableName'] == 'NIFTYFUT', 'Symbol'] = currentNiftyFut
        changesMade = f"{changesMade}\nNiftyFut updated from {niftyFutInLookup} to {currentNiftyFut}"        
        lookupTableChanged = True

    #Find the existing BANKNIFTYFUT symbol in lookupTable and replace it if necessary        
    bankNiftyFutInLookup = lookupTable[lookupTable['TableName'] == 'BANKNIFTYFUT']['Symbol'].iloc[0]
    if bankNiftyFutInLookup != currentBankNiftyFut:
        #NiftyFut Symbol needs to be updated
        lookupTable.loc[lookupTable['TableName'] == 'BANKNIFTYFUT', 'Symbol'] = currentBankNiftyFut
        changesMade = f"{changesMade}\nBankNiftyFut updated from {bankNiftyFutInLookup} to {currentBankNiftyFut}"        
        lookupTableChanged = True    

    
    if lookupTableChanged:        
        #Saving original files before replacing and updating.
        #This might be required to investigate potential issues with symbol and table updates to the lookup file
        #Lookup Table
        referenceLookupTableName = currentLookUpFileName.replace('.csv','_'+str(date.today())+'.csv')
        referenceLookupTablePath = path.join(lookUpFilesDir,referenceLookupTableName)
        shutil.copy(currentLookupTablePath,referenceLookupTablePath)
        
        #NSE 500 List
        todayNSE500TodayListName = f"ind_nifty500_list_{str(date.today())}.csv"
        # Read the CSV file from the URL and save it directly
        #Pandas could have been skipped here, using requests. Using Pandas as it has lesser operations between read and write
        response = requests.get(n500url, headers={'User-Agent': generateRandomUserAgent()})
        csv_data = StringIO(response.text)
        nse500df = pd.read_csv(csv_data)
        nse500df.to_csv(path.join(lookUpFilesDir,todayNSE500TodayListName), index=False)
        
        #Arranging lookupTable alphabetically before overwriting the local lookup file
        lookupTable = lookupTable.sort_values(by='Symbol')
        
        #Replacing Original Looup File with updated list
        lookupTable.to_csv(currentLookupTablePath,index=False)
        changesMade = changesMade+f'\n\n{todayNSE500TodayListName} and {referenceLookupTableName} backed up for reference\n'
        msg = 'lookup Table lookupTables_Nifty500.csv Updated'
        nifty500UpdateChangelogger(msg)
        nifty500UpdateChangelogger(changesMade)
        #mail(destinationEmailAddress, 'DAS Main - Access token Failed.',msg)     
        DAS_mailer('DAS - lookupTables_Nifty500 Updated',changesMade)        
        
    else:
        msg = 'DAS - lookupTables_Nifty500 - No changes made to the lookupFile'
        nifty500UpdateMainlogger(msg)

def nifty500Updater():   
    try:
        if  path.exists(path.join(lookUpFilesDir,currentLookUpFileName)):
            updateSymbolTableNameList()
        else:
            createSymbolTableNameList()
        return True
    except Exception as e:
        msg = f'nifty500Updater failed with excpetion {e}. Traceback - {str(traceback.format_exc())}'
        nifty500UpdateMainlogger(msg)
        DAS_errorLogger('nifty500Updater - '+msg)
        DAS_mailer('DAS - nifty500Updater FAIL!!!',msg)    
        return False

if __name__=='__main__':
    nifty500Updater()
    