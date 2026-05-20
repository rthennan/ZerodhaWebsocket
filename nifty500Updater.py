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
    - Only exceptions are NIFTYFUT, BANKNIFTYFUT and SENSEXFUT as the symbol changes every month
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
            Hence when you read data, you would have to Union AMARAJABAT and ARE_M to get the full picture.
     - The small tables report sent at the end of every day and nifty500_SymbolsChanged.log can be used to manage this situation
     - Delisted stocks won't be removed from the existing lookupTables_Nifty500.csv file

ChangeLog for symbols identified manually:
    - Amara Raja Energy & Mobility Ltd.Changed from AMARAJABAT (Table Name AMARAJABAT) to ARE&M (Table Name ARE_M)
      in September 2023.
    - Kennametal India Limited (KENNAET) was removed from the NSE on October 26, 2023
    - TATACOFFEE delisted - https://tradingqna.com/t/everything-you-need-to-know-about-merger-of-tata-coffee-with-tata-consumer-products/158981
    - WELSPUNIND to WELSPUNLIV on 14 Dec 2023
    - ADANITRANS to ADANIENSOL with effect from August 24, 2023
    - MFL changed to EPIGRAL with effect from September 11, 2023

ChangeLog 2024-09-23:
    Nifty 500 list URL changed from https://archives.nseindia.com/content/indices/ind_nifty500list.csv
    to https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv
    And NSE seems to have started blocking programmatic access.
    Hence mimicking a user-agent and extracting CSV from the response text.

ChangeLog 2025-08-07:
    - getCurrentFuture for Nifty and BankNifty previously checked LastThursday and LastWednesday.
    - Fixed them to rely purely on the Zerodha instrument dump, dynamically finding the active Future for today.
    - Resilient to changes in the expiry day.

ChangeLog 2026-05-19:
    - Adding Sensex Spot and Futures.
    - getNifty500SymbolList is now more resilient.
    - Tries to get the list from NSE first (see n500url) and uses existing cached CSV as fallback.
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
import urllib.request


numbOfRetries = 5

lookUpFilesDir = 'lookupTables'
currentLookUpFileName = 'lookupTables_Nifty500.csv'
currentLookupTablePath = path.join(lookUpFilesDir, currentLookUpFileName)
n500url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


def ensureLookUpFilesDir():
    if not path.exists(lookUpFilesDir):
        makedirs(lookUpFilesDir)


def nifty500UpdateMainlogger(txt):
    print(dt.now(), 'nifty500UpdateRun', txt)

    logDirectory = path.join('Logs', str(date.today()) + '_DAS_Logs')

    if not path.exists(logDirectory):
        makedirs(logDirectory)

    logFile = path.join(logDirectory, f'DAS_nifty500UpdateRun_logs_{str(date.today())}.log')
    logMsg = '\n' + str(dt.now()) + '    ' + txt

    with open(logFile, 'a') as f:
        f.write(logMsg)


def nifty500UpdateChangelogger(txt):
    print(dt.now(), 'nifty500_SymbolsChanged', txt)

    logFile = 'nifty500_SymbolsChanged.log'
    logMsg = '\n' + str(dt.now()) + '    ' + txt

    with open(logFile, 'a') as f:
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

    platform = random.choice(platforms)
    browser, versions = random.choice(browsers)
    version = random.choice(versions)

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


def downloadZerodhaInstrumentFile():
    ensureLookUpFilesDir()

    zerodhaDumpUrl = 'https://api.kite.trade/instruments'
    zerdhaIstrumentDumpFileName = 'zerodhaInstrumentDump.csv'
    zerdhaIstrumentDumpFilePath = path.join(lookUpFilesDir, zerdhaIstrumentDumpFileName)

    for attempt in range(1, numbOfRetries + 1):
        try:
            urllib.request.urlretrieve(zerodhaDumpUrl, zerdhaIstrumentDumpFilePath)

            msg = 'Downloaded Instrument dump file from Zerodha'
            nifty500UpdateMainlogger(msg)

            return None

        except Exception as e:
            msg = (
                f'Downloading zerodhaInstrumentsDump from {zerodhaDumpUrl} failed. '
                f'Attempt No: {attempt}/{numbOfRetries}. '
                f'Exception -> {e} Traceback: {traceback.format_exc()}'
            )

            nifty500UpdateMainlogger(msg)
            DAS_errorLogger('lookupTablesCreator - ' + msg)

            if attempt < numbOfRetries:
                sleep(30)

    msg = f'Downloading zerodhaInstrumentsDump from {zerodhaDumpUrl} failed after {numbOfRetries} attempts. Exiting'

    nifty500UpdateMainlogger(msg)
    DAS_errorLogger('lookupTablesCreator - ' + msg)

    sys.exit()


# Not importing this from lookupTableCreator, to avoid dependency just for this one function
def getZerodhaInstDump():
    ensureLookUpFilesDir()

    zerdhaIstrumentDumpFileName = 'zerodhaInstrumentDump.csv'
    zerdhaIstrumentDumpFilePath = path.join(lookUpFilesDir, zerdhaIstrumentDumpFileName)

    if path.exists(zerdhaIstrumentDumpFilePath):
        oneHourAgo = dt.now() - timedelta(hours=1)

        zerodhaDumpModifiedTime = dt.fromtimestamp(path.getmtime(zerdhaIstrumentDumpFilePath))

        if zerodhaDumpModifiedTime >= oneHourAgo:
            msg = f'local zerdhaIstrumentDumpFile {zerdhaIstrumentDumpFileName} is fresh. Using it.'
            nifty500UpdateMainlogger(msg)
        else:
            msg = f'local zerodhaInstrumentDumpFile {zerdhaIstrumentDumpFileName} is older than 1 hour. Downloading a new one'
            nifty500UpdateMainlogger(msg)
            downloadZerodhaInstrumentFile()

    else:
        msg = f'local zerodhaInstrumentDumpFile {zerdhaIstrumentDumpFileName} not found. Downloading a new one'
        nifty500UpdateMainlogger(msg)
        downloadZerodhaInstrumentFile()

    return pd.read_csv(zerdhaIstrumentDumpFilePath)


def getCurrentFuture(index_name):
    """
    Get current month future for given index.

    Args:
        index_name (str): 'NIFTY' or 'BANKNIFTY' or 'SENSEX'

    Returns:
        str: Trading symbol of the current month future
    """

    zerodhaInstrumentsDump = getZerodhaInstDump()

    filteredDF = zerodhaInstrumentsDump[
        (zerodhaInstrumentsDump['segment'].isin(['NFO-FUT', 'BFO-FUT'])) &
        (zerodhaInstrumentsDump['name'] == index_name)
    ]

    if filteredDF.empty:
        raise ValueError(f'No futures found for {index_name} in Zerodha instrument dump')

    fut_expiries = filteredDF['expiry'].dropna().unique().tolist()

    if len(fut_expiries) == 0:
        raise ValueError(f'No valid futures expiry found for {index_name} in Zerodha instrument dump')

    thisFutExpiryDate = min(fut_expiries, key=lambda d: dt.strptime(d, "%Y-%m-%d"))

    currentFutureRows = filteredDF[filteredDF['expiry'] == thisFutExpiryDate]

    if currentFutureRows.empty:
        raise ValueError(f'No future row found for {index_name} with expiry {thisFutExpiryDate}')

    currentFuture = currentFutureRows['tradingsymbol'].iloc[0]

    return currentFuture


def replaceSpecial(intext):
    # Remove '-BE' only if found at the end of the symbol name.
    # Subscribe to BE symbols, but store tick data in table name without the BE flag.
    # This way, if/when the BE flag gets removed, the data will still be in the same table.
    if intext[-3:] == '-BE':
        intext = intext[:-3]

    # Replace non table-name-friendly special characters with _
    return intext.replace('-', '_').replace('&', '_')


def getStocksWithOptions():
    zerodhaInstrumentsDump = getZerodhaInstDump()

    stockInstrumentsOnly = zerodhaInstrumentsDump.copy(deep=True)
    stockInstrumentsOnly = stockInstrumentsOnly[
        (stockInstrumentsOnly['instrument_type'] == 'EQ') &
        (stockInstrumentsOnly['segment'] == 'NSE')
    ]

    stockInstList = stockInstrumentsOnly['tradingsymbol'].tolist()

    stockOptionsOnly = zerodhaInstrumentsDump.copy(deep=True)
    stockOptionsOnly = stockOptionsOnly[
        stockOptionsOnly['segment'] == 'NFO-OPT'
    ]

    stockOptionsOnly_names = list(stockOptionsOnly['name'].unique())

    # Equities that have stock options
    stocksWithOptions = sorted(list(set(stockInstList) & set(stockOptionsOnly_names)))

    return sorted(stocksWithOptions)


def getNifty500SymbolList():
    ensureLookUpFilesDir()

    fallbackFile = path.join(lookUpFilesDir, 'ind_nifty500list.csv')

    def processNifty500DF(nifty500FromNSE):
        nifty500FromNSE = nifty500FromNSE.copy()

        requiredCols = {'Symbol', 'Series'}
        missingCols = requiredCols - set(nifty500FromNSE.columns)

        if missingCols:
            raise ValueError(f'Missing required columns in Nifty 500 CSV: {missingCols}')

        if nifty500FromNSE.empty:
            raise ValueError('Nifty 500 CSV is empty')

        # Drop rows where Symbol itself is missing before converting to string
        nifty500FromNSE = nifty500FromNSE.dropna(subset=['Symbol'])

        nifty500FromNSE['Symbol'] = nifty500FromNSE['Symbol'].astype(str).str.strip()
        nifty500FromNSE['Series'] = nifty500FromNSE['Series'].astype(str).str.strip()

        # Remove blank symbols if any
        nifty500FromNSE = nifty500FromNSE[nifty500FromNSE['Symbol'] != '']

        nifty500FromNSE.loc[
            (nifty500FromNSE['Series'] == 'BE') &
            (~nifty500FromNSE['Symbol'].str.endswith('-BE')),
            'Symbol'
        ] += '-BE'

        return nifty500FromNSE['Symbol'].tolist()

    def mergeWithStocksWithOptions(n500List):
        try:
            stocksWithOptionsList = getStocksWithOptions()
            return sorted(set(n500List + stocksWithOptionsList))

        except Exception as e:
            msg = (
                f'getNifty500SymbolList: getStocksWithOptions failed. '
                f'Proceeding with Nifty 500 list only. '
                f'Exception: {e}\n{traceback.format_exc()}'
            )

            nifty500UpdateMainlogger(msg)
            DAS_errorLogger('nifty500Updater - ' + msg)

            return sorted(n500List)

    # ── Stage 1: Try live NSE URL ──────────────────────────────────────
    for attempt in range(1, numbOfRetries + 1):
        try:
            response = requests.get(
                n500url,
                headers={'User-Agent': generateRandomUserAgent()},
                timeout=(10, 30)
            )

            response.raise_for_status()

            nifty500FromNSE = pd.read_csv(StringIO(response.text))

            # Validate/process before accepting the file as good
            n500List = processNifty500DF(nifty500FromNSE)

            # Save raw NSE CSV, not the processed -BE-modified version
            nifty500FromNSE.to_csv(fallbackFile, index=False)

            msg = 'getNifty500SymbolList: Success from Live NSE.'
            nifty500UpdateMainlogger(msg)

            return mergeWithStocksWithOptions(n500List)

        except Exception as e:
            msg = (
                f'getNifty500SymbolList: Live NSE attempt {attempt}/{numbOfRetries} failed. '
                f'Exception: {e}\n{traceback.format_exc()}'
            )

            nifty500UpdateMainlogger(msg)
            DAS_errorLogger('nifty500Updater - ' + msg)

            if attempt < numbOfRetries:
                sleep(30)

    # ── Stage 2: Network exhausted — fall back to local CSV ────────────
    msg = (
        f'getNifty500SymbolList: All {numbOfRetries} live NSE attempts failed. '
        f'Falling back to local CSV: {fallbackFile}'
    )

    nifty500UpdateMainlogger(msg)
    DAS_errorLogger('nifty500Updater - ' + msg)
    DAS_mailer('DAS Nifty 500 - Live fetch failed, using cached CSV', msg)

    try:
        nifty500FromNSE = pd.read_csv(fallbackFile)
        n500List = processNifty500DF(nifty500FromNSE)

        return mergeWithStocksWithOptions(n500List)

    except Exception as e:
        msg = (
            f'getNifty500SymbolList: Fallback CSV also failed. Exiting execution. '
            f'Exception: {e}\n{traceback.format_exc()}'
        )

        nifty500UpdateMainlogger(msg)
        DAS_errorLogger('nifty500Updater - ' + msg)
        DAS_mailer('DAS Nifty 500 - Both live and fallback CSV failed. Exiting', msg)

        sys.exit()


def createSymbolTableNameList():
    ensureLookUpFilesDir()

    msg = f'{path.join(lookUpFilesDir, currentLookUpFileName)} not found. Creating a new lookupTable'
    nifty500UpdateMainlogger(msg)
    nifty500UpdateChangelogger(msg)

    # Create a new dataframe with Symbol and TableName columns
    lookupTable = pd.DataFrame(columns=['Symbol', 'TableName'])

    # Add Nifty, BankNifty and Sensex indices
    indexesToAdd = [
        {'Symbol': 'NIFTY 50', 'TableName': 'NIFTY'},
        {'Symbol': 'NIFTY BANK', 'TableName': 'BANKNIFTY'},
        {'Symbol': 'SENSEX', 'TableName': 'SENSEX'}
    ]

    indexesToAdd_df = pd.DataFrame(indexesToAdd)

    lookupTable = pd.concat([lookupTable, indexesToAdd_df], ignore_index=True)

    # Add Nifty, BankNifty and Sensex Futures
    niftyCurrentFuture = getCurrentFuture('NIFTY')
    bankNiftyCurrentFuture = getCurrentFuture('BANKNIFTY')
    sensexCurrentFuture = getCurrentFuture('SENSEX')

    futuresToAdd = [
        {'Symbol': niftyCurrentFuture, 'TableName': 'NIFTYFUT'},
        {'Symbol': bankNiftyCurrentFuture, 'TableName': 'BANKNIFTYFUT'},
        {'Symbol': sensexCurrentFuture, 'TableName': 'SENSEXFUT'}
    ]

    futuresToAdd_df = pd.DataFrame(futuresToAdd)

    lookupTable = pd.concat([lookupTable, futuresToAdd_df], ignore_index=True)

    # Get Nifty 500 list
    nifty500SymbolList = getNifty500SymbolList()
    nifty500SymbolsDF = pd.DataFrame({'Symbol': sorted(nifty500SymbolList)})

    # Create a TableName column
    nifty500SymbolsDF['TableName'] = nifty500SymbolsDF['Symbol'].apply(lambda x: replaceSpecial(x))

    # Add Nifty 500 to the lookup table
    lookupTable = pd.concat([lookupTable, nifty500SymbolsDF], ignore_index=True)

    # Arrange alphabetically
    lookupTable = lookupTable.sort_values(by='Symbol')

    newLookupTableFilePath = path.join(lookUpFilesDir, currentLookUpFileName)
    lookupTable.to_csv(newLookupTableFilePath, index=False)

    msg = 'lookup Table lookupTables_Nifty500.csv not found. Created it'
    nifty500UpdateChangelogger(msg)

    DAS_mailer('DAS - lookupTables_Nifty500 created', msg)


def upsertFutureSymbol(lookupTable, tableName, currentFuture, label, changesMade):
    futureRows = lookupTable[lookupTable['TableName'] == tableName]

    if futureRows.empty:
        futureToAdd = pd.DataFrame([
            {'Symbol': currentFuture, 'TableName': tableName}
        ])

        lookupTable = pd.concat([lookupTable, futureToAdd], ignore_index=True)
        changesMade = f"{changesMade}\n{label} added: {currentFuture}"

        return lookupTable, changesMade, True

    futureInLookup = futureRows['Symbol'].iloc[0]

    if futureInLookup != currentFuture:
        lookupTable.loc[lookupTable['TableName'] == tableName, 'Symbol'] = currentFuture
        changesMade = f"{changesMade}\n{label} updated from {futureInLookup} to {currentFuture}"

        return lookupTable, changesMade, True

    return lookupTable, changesMade, False


def upsertFixedSymbol(lookupTable, symbol, tableName, label, changesMade):
    tableRows = lookupTable[lookupTable['TableName'] == tableName]

    if tableRows.empty:
        rowToAdd = pd.DataFrame([
            {'Symbol': symbol, 'TableName': tableName}
        ])

        lookupTable = pd.concat([lookupTable, rowToAdd], ignore_index=True)
        changesMade = f"{changesMade}\n{label} added: {symbol} -> {tableName}"

        return lookupTable, changesMade, True

    symbolInLookup = tableRows['Symbol'].iloc[0]

    if symbolInLookup != symbol:
        lookupTable.loc[lookupTable['TableName'] == tableName, 'Symbol'] = symbol
        changesMade = f"{changesMade}\n{label} updated from {symbolInLookup} to {symbol}"

        return lookupTable, changesMade, True

    return lookupTable, changesMade, False

def updateSymbolTableNameList():
    ensureLookUpFilesDir()

    lookupTableChanged = False
    changesMade = ''

    lookupTable = pd.read_csv(path.join(lookUpFilesDir, currentLookUpFileName))
    
    # Ensure NIFTY, BANKNIFTY and SENSEX index rows exist/update correctly
    indexesToEnsure = [
        {'Symbol': 'NIFTY 50', 'TableName': 'NIFTY', 'Label': 'Nifty Index'},
        {'Symbol': 'NIFTY BANK', 'TableName': 'BANKNIFTY', 'Label': 'BankNifty Index'},
        {'Symbol': 'SENSEX', 'TableName': 'SENSEX', 'Label': 'Sensex Index'}
    ]
    
    for indexRow in indexesToEnsure:
        lookupTable, changesMade, changed = upsertFixedSymbol(
            lookupTable=lookupTable,
            symbol=indexRow['Symbol'],
            tableName=indexRow['TableName'],
            label=indexRow['Label'],
            changesMade=changesMade
        )
    
        lookupTableChanged = lookupTableChanged or changed

    # Checking if Nifty 500 list has new symbols
    existingSymbols = lookupTable['Symbol'].tolist()
    n500currentSymbols = getNifty500SymbolList()

    missingSymbols = list(set(n500currentSymbols) - set(existingSymbols))

    if len(missingSymbols) > 0:
        symbolsToAdd = pd.DataFrame({'Symbol': sorted(missingSymbols)})

        # Create new table names for new symbols, replacing special characters
        symbolsToAdd['TableName'] = symbolsToAdd['Symbol'].apply(lambda x: replaceSpecial(x))

        lookupTable = pd.concat([lookupTable, symbolsToAdd], ignore_index=True)

        msg = f'Found {len(missingSymbols)} new symbol(s) in Nifty500 list.'
        nifty500UpdateChangelogger(msg)
        nifty500UpdateMainlogger(msg)

        changesMade = changesMade + '\nSymbol  TableName'

        for row in range(len(symbolsToAdd)):
            changesMade = f"{changesMade}\n{symbolsToAdd['Symbol'].iloc[row]}  {symbolsToAdd['TableName'].iloc[row]}  "

        lookupTableChanged = True
        
    

    # Check if NIFTYFUT, BANKNIFTYFUT and SENSEXFUT have to be inserted/updated
    currentNiftyFut = getCurrentFuture('NIFTY')
    currentBankNiftyFut = getCurrentFuture('BANKNIFTY')
    currentSensexFut = getCurrentFuture('SENSEX')

    lookupTable, changesMade, changed = upsertFutureSymbol(
        lookupTable=lookupTable,
        tableName='NIFTYFUT',
        currentFuture=currentNiftyFut,
        label='NiftyFut',
        changesMade=changesMade
    )
    lookupTableChanged = lookupTableChanged or changed

    lookupTable, changesMade, changed = upsertFutureSymbol(
        lookupTable=lookupTable,
        tableName='BANKNIFTYFUT',
        currentFuture=currentBankNiftyFut,
        label='BankNiftyFut',
        changesMade=changesMade
    )
    lookupTableChanged = lookupTableChanged or changed

    lookupTable, changesMade, changed = upsertFutureSymbol(
        lookupTable=lookupTable,
        tableName='SENSEXFUT',
        currentFuture=currentSensexFut,
        label='SensexFut',
        changesMade=changesMade
    )
    lookupTableChanged = lookupTableChanged or changed

    if lookupTableChanged:
        # Saving original files before replacing and updating.
        # This may be required to investigate potential issues with symbol and table updates.

        # Lookup table backup
        referenceLookupTableName = currentLookUpFileName.replace('.csv', '_' + str(date.today()) + '.csv')
        referenceLookupTablePath = path.join(lookUpFilesDir, referenceLookupTableName)

        shutil.copy(currentLookupTablePath, referenceLookupTablePath)

        # NSE 500 list backup
        todayNSE500TodayListName = f"ind_nifty500_list_{str(date.today())}.csv"
        cachedNSE500FilePath = path.join(lookUpFilesDir, 'ind_nifty500list.csv')
        todayNSE500TodayListPath = path.join(lookUpFilesDir, todayNSE500TodayListName)

        if path.exists(cachedNSE500FilePath):
            shutil.copy(cachedNSE500FilePath, todayNSE500TodayListPath)
        else:
            msg = (
                f'Cached NSE 500 file not found at {cachedNSE500FilePath}. '
                f'Skipping NSE 500 dated backup.'
            )

            nifty500UpdateMainlogger(msg)
            DAS_errorLogger('nifty500Updater - ' + msg)

        # Arrange lookupTable alphabetically before overwriting the local lookup file
        lookupTable = lookupTable.sort_values(by='Symbol')

        # Replace original lookup file with updated list
        lookupTable.to_csv(currentLookupTablePath, index=False)

        changesMade = changesMade + f'\n\n{todayNSE500TodayListName} and {referenceLookupTableName} backed up for reference\n'

        msg = 'lookup Table lookupTables_Nifty500.csv Updated'
        nifty500UpdateChangelogger(msg)
        nifty500UpdateChangelogger(changesMade)

        DAS_mailer('DAS - lookupTables_Nifty500 Updated', changesMade)

    else:
        msg = 'DAS - lookupTables_Nifty500 - No changes made to the lookupFile'
        nifty500UpdateMainlogger(msg)


def nifty500Updater():
    try:
        ensureLookUpFilesDir()

        if path.exists(path.join(lookUpFilesDir, currentLookUpFileName)):
            updateSymbolTableNameList()
        else:
            createSymbolTableNameList()

        return True

    except Exception as e:
        msg = f'nifty500Updater failed with excpetion {e}. Traceback - {str(traceback.format_exc())}'

        nifty500UpdateMainlogger(msg)
        DAS_errorLogger('nifty500Updater - ' + msg)
        DAS_mailer('DAS - nifty500Updater FAIL!!!', msg)

        return False


if __name__ == '__main__':
    nifty500Updater()