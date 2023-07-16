# -*- coding: utf-8 -*-
"""
Created on Sun Jul 16 17:35:37 2023
Fully automating this is not optimal as it will not work for symbol changes.
1. Check small tables and update / remove symbol name
    Update - Update new symbol on symbol change
    Remove - remove on delisting
2. Then run the below code and identify missing symbols
   Add the new symbols to instrumentsLookup_DAS5_4.xlsx
"""

import pandas as pd
from os import path, makedirs
import requests
import csv
import datetime
from datetime import datetime as dt

def log(txt):
    directory = path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
    if not path.exists(directory):
        makedirs(directory)
    logFile = path.join(directory,str(datetime.date.today())+'_nifty500downloader.log')
    logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

n500url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"


lookUpFilesDir = 'lookup_tables'
lookupTB1 = 'instrumentsLookup.xlsx'
lookupTB2 = 'instrumentsLookup_DAS5_2.xlsx'
lookupTB3 = 'instrumentsLookup_DAS5_3.xlsx'
lookupTB4 = 'instrumentsLookup_DAS5_4.xlsx'

lookupTable = pd.read_excel(path.join(lookUpFilesDir,lookupTB1))

for tb in [lookupTB2, lookupTB3, lookupTB4]:
    newtb = pd.read_excel(path.join(lookUpFilesDir,tb))
    print(tb, newtb.shape)
    lookupTable = pd.concat([lookupTable, newtb])

existingsymbols = lookupTable['Symbol'].tolist()

def replaceSpecial(intext):
    return intext.replace('-', '_').replace('&', '_')

try:
    nifty500OG = pd.read_csv(n500url)
    symbolsToday = nifty500OG['Symbol'].tolist()  
    missing_symbols = list(set(symbolsToday) - set(existingsymbols))
    msg = f'Missing {len(missing_symbols)} symbols'
    print(dt.now(),msg)
    log(msg)
    newSymbols = pd.DataFrame({'Symbol': sorted(missing_symbols)})
    newSymbols['Table'] = newSymbols['Symbol'].apply(lambda x: replaceSpecial(x))
    newSymbols.to_excel(str(datetime.date.today())+'_missingsymbols.xlsx', index=False)

except Exception as e:
    msg = f'Downloading nse 500 list failed withe xcpetion {e}'
    print(dt.now(), msg)
    log(msg)
    
    