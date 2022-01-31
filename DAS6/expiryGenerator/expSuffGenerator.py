# -*- coding: utf-8 -*-
"""
Created on Sat Jan 25 17:24:59 2020

@author: Thennan
Assuming there are no trading holidays in the first two weeks of January
Run this program with the expiryGenerator directory
Check https://kite.trade/forum/discussion/5574/change-in-format-of-weekly-options-instruments for the naming convention
"""
import pandas as pd
import calendar
from datetime import datetime as dt,timedelta as tdel
from dateutil.relativedelta import relativedelta, TH
from os import path

holidaysFile = 'tradingHolidays.csv' #Needs be in the same folder. i.e Parent Folder of DAS6

holidays = pd.read_csv(holidaysFile)['Date'].values.tolist()
#The table prefixes are based on the year for which the tradingHolidays have been provided.
#The year is fetched from the first entry in the tradingHolidays list


def strToDate(inDate2):
    return dt.strptime(str(inDate2), '%Y-%m-%d').date()

def isLastThursday(inDate1):
    inDate1 = dt.strptime(str(inDate1), '%Y-%m-%d').date()
    lastDayofMonth = calendar.monthrange(inDate1.year,inDate1.month)[1]
    lastDateOfTheMonth = (inDate1.replace(day = lastDayofMonth))
    lastThursday = lastDateOfTheMonth    
    while lastThursday.weekday() != calendar.THURSDAY:
        lastThursday = lastThursday-tdel(days=1)        
    if inDate1 == lastThursday:
        return True
    else:
        return False

def monthExp(inDate3):
    inDate3 = dt.strptime(str(inDate3), '%Y-%m-%d').date()
    return (str(inDate3.year)[2:])+(str(calendar.month_name[inDate3.month]).upper()[:3])

def normExp(inDate3):
    inDate3 = dt.strptime(str(inDate3), '%Y-%m-%d').date()
    if inDate3.month < 10:
        return str(inDate3.year)[2:]+str(inDate3.month)+('0'+str(inDate3.day))[-2:]
    elif 10 <= inDate3.month <= 12:
        return str(inDate3.year)[2:]+(str(calendar.month_name[inDate3.month]).upper()[0])+('0'+str(inDate3.day))[-2:]
        
        
def expSuffix(inDate, indexName):
    indexName = indexName.upper()
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    thisThursday = inDate + relativedelta(weekday=TH(0))
    while str(thisThursday) in holidays:
        thisThursday = thisThursday - tdel(days=1)  
    if thisThursday.month != inDate.month:
        return indexName+normExp(thisThursday)
    else:
        if isLastThursday(thisThursday):
            return indexName+monthExp(thisThursday)
        else:
            return indexName+normExp(thisThursday)


year = holidays[0][0:4]
startDate = strToDate(str(year)+'-01-01')
endDateActual = strToDate(str(year)+'-12-31') 
endDate = endDateActual + tdel(days=7)
tradeDays = []    
weeknds = [calendar.SATURDAY,calendar.SUNDAY]

while startDate <= endDate:
    if (startDate.weekday() not in weeknds) and (str(startDate) not in holidays):
        tradeDays.append(startDate)
    else:
        pass
    startDate = startDate + tdel(days=1) 
   
#NiftyTable
#def expSuffix(inDate, indexName):

def expGenMain(indexNameIn):
    expLookup = pd.DataFrame(tradeDays,columns = ['date'])
    #Generating the Current Expiry using the expSuffix function.
    expLookup['currExpiry'] = expLookup['date'].apply(expSuffix,indexName = indexNameIn)
    
    #Just copying the next expiry and sliding it around, to get the next expiry
    nextExpList = expLookup.currExpiry.unique()
    nextExpCounter = 1
    expLookup['nextExpiry'] = nextExpList[nextExpCounter]
    
    for x in range(len(expLookup)-1):
        expLookup['nextExpiry'].iloc[x] = nextExpList[nextExpCounter]
        if (expLookup['currExpiry'].iloc[x] != expLookup['currExpiry'].iloc[x+1]):
            nextExpCounter = nextExpCounter+1
        if nextExpCounter >= len(nextExpList):
            break
    #Trimming the expiry list just to the current year
    #The last entry for the next expiry column (before trimmming) would have been incorrect anyway
    expLookup = expLookup[expLookup['date'] <= endDateActual] 
    fileName = 'nfo_simmonsLookup.csv' if indexNameIn.upper() == 'NIFTY' else 'bnfo_simmonsLookup.csv'
    filePath = path.join('..','lookup_tables',fileName)
    expLookup.to_csv(filePath,index = False) 
    return fileName
    

niftyOptFile = expGenMain('NIFTY') #Generating the expiry suffix for Nifty
BankNiftyOptFile = expGenMain('BANKNIFTY') #Generating the expiry suffix for BankNifty

print(f'{niftyOptFile} and {BankNiftyOptFile} stored successfully in DAS6/lookup_tables')