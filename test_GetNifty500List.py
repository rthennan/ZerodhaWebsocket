#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 19 10:37:11 2026

@author: rajesh
Standalone Tester for Nifty 500 fetch
"""

import pandas as pd
from datetime import datetime as dt, date
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


def test_GetNiftyLogger(txt):
    print(dt.now(),'TEST_nifty500UpdateRun',txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory): 
        makedirs(logDirectory) 
    logFile = path.join(logDirectory,f'test_GETNifty500List_{str(date.today())}.log')
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
    test_GetNiftyLogger(msg)
    return user_agent


def getStocksWithOptions():
    zerodhaDumpUrl = 'https://api.kite.trade/instruments'
    zerodhaInstrumentsDump = pd.read_csv(zerodhaDumpUrl)    
    stockInstrumentsOnly = zerodhaInstrumentsDump.copy(deep=True)
    stockInstrumentsOnly = stockInstrumentsOnly[
        (stockInstrumentsOnly['instrument_type'] == 'EQ') & 
        (stockInstrumentsOnly['segment'] == 'NSE')
    ]    
    stockInstList = stockInstrumentsOnly['tradingsymbol'].tolist()
    stockOptionsOnly = zerodhaInstrumentsDump.copy(deep=True)
    stockOptionsOnly = stockOptionsOnly[
        (stockOptionsOnly['segment'] == 'NFO-OPT')
    ]
    stockOptionsOnly_names = list(stockOptionsOnly['name'].unique())    
    #Equities that have stockOptions
    stocksWithOptions =  sorted(list(set(stockInstList) & set(stockOptionsOnly_names)))  
    
    return sorted(stocksWithOptions)

def getNifty500SymbolList():

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

            test_GetNiftyLogger(msg)
            DAS_errorLogger('nifty500Updater - ' + msg)

            return sorted(n500List)

    # ── Stage 1: Try live NSE URL ──────────────────────────────────────
    for attempt in range(1, numbOfRetries + 1):
        try:
            response = requests.get(
                n500url,
                headers={'User-Agent': generateRandomUserAgent()},
                timeout=(10, 30)  # (connect_timeout, read_timeout)
            )

            response.raise_for_status()

            nifty500FromNSE = pd.read_csv(StringIO(response.text))

            # Validate/process before accepting the file as good
            n500List = processNifty500DF(nifty500FromNSE)

            # Save raw NSE CSV, not the processed -BE-modified version
            nifty500FromNSE.to_csv(fallbackFile, index=False)

            msg = (
                'getNifty500SymbolList: Success from Live NSE.'
            )

            test_GetNiftyLogger(msg)
            return mergeWithStocksWithOptions(n500List)

        except Exception as e:
            msg = (
                f'getNifty500SymbolList: Live NSE attempt {attempt}/{numbOfRetries} failed. '
                f'Exception: {e}\n{traceback.format_exc()}'
            )

            test_GetNiftyLogger(msg)
            DAS_errorLogger('nifty500Updater - ' + msg)

            if attempt < numbOfRetries:
                sleep(30)

    # ── Stage 2: Network exhausted — fall back to local CSV ────────────
    msg = (
        f'getNifty500SymbolList: All {numbOfRetries} live NSE attempts failed. '
        f'Falling back to local CSV: {fallbackFile}'
    )

    test_GetNiftyLogger(msg)
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

        test_GetNiftyLogger(msg)
        DAS_errorLogger('nifty500Updater - ' + msg)
        DAS_mailer('DAS Nifty 500 - Both live and fallback CSV failed. Exiting', msg)

        sys.exit()
        
if __name__ =='__main__':
    msg = 'test_GetNifty500List - Running getNifty500SymbolList standalone'
    test_GetNiftyLogger(msg)
    
    nifty500SymbolList = getNifty500SymbolList()
    nifty500SymbolsDF = pd.DataFrame({'Symbol': sorted(nifty500SymbolList)})
    nifty500SymbolsDF.to_csv(path.join(lookUpFilesDir, f'test_Nifty500Symbols_{str(date.today())}.csv'), index=False)
    