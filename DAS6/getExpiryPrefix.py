import pandas as pd
import calendar
from datetime import datetime as dt,timedelta as tdel, date
from dateutil.relativedelta import relativedelta, TH, WE
from os import path
"""
ChangeLog:
    21Sep2023:
        Banknifty weekly expiry day changed to Wednesday
        https://zerodha.com/marketintel/bulletin/358889/revision-in-expiry-day-for-banknifty-weekly-options-contracts
        
"""

#trade holidays Path
holsFilePath = path.join('..','tradeHoliday', 'tradingHolidays.csv')
hols = pd.read_csv(holsFilePath)
holidays = hols['Date'].values.tolist()

def normExp(inDate3):
    if inDate3.month < 10:
        return str(inDate3.year)[2:]+str(inDate3.month)+('0'+str(inDate3.day))[-2:]
    elif 10 <= inDate3.month <= 12:
        return str(inDate3.year)[2:]+(str(calendar.month_name[inDate3.month]).upper()[0])+('0'+str(inDate3.day))[-2:]

def monthExp(inDate3):
    inDate3 = dt.strptime(str(inDate3), '%Y-%m-%d').date()
    return (str(inDate3.year)[2:])+(str(calendar.month_name[inDate3.month]).upper()[:3])

def isLastThursday(date_to_check):
    date_to_check = dt.strptime(str(date_to_check), '%Y-%m-%d').date() 
    # Check if the given date is a Thursday (weekday index 3)
    if date_to_check.weekday() != calendar.THURSDAY:
        return False

    # Get the year and month from the given date
    year = date_to_check.year
    month = date_to_check.month

    # Find the last day of the month
    last_day = calendar.monthrange(year, month)[1]

    # Calculate the date for the last Thursday of the month
    last_thursday = date(year, month, last_day)

    # Find the weekday index of the last Thursday
    while last_thursday.weekday() != calendar.THURSDAY:
        last_thursday -= tdel(days=1)

    # Check if the given date is the last Thursday
    return date_to_check == last_thursday
    
def isPenUltimateThursday(date_to_check):
    date_to_check = dt.strptime(str(date_to_check), '%Y-%m-%d').date() 
    # Check if the given date is a Thursday (weekday index 3)
    if date_to_check.weekday() != calendar.THURSDAY:
        return False

    # Get the year and month from the given date
    year = date_to_check.year
    month = date_to_check.month

    # Find the last day of the month
    last_day = calendar.monthrange(year, month)[1]

    # Calculate the date for the last Thursday of the month
    last_thursday = date(year, month, last_day)

    # Find the weekday index of the last Thursday
    while last_thursday.weekday() != calendar.THURSDAY:
        last_thursday -= tdel(days=1)
        
    # Calculate the date for the penultimate Thursday
    penultimate_thursday = last_thursday - tdel(weeks=1)        

    # Check if the given date is the last Thursday or the penultimate Thursday
    return (date_to_check == last_thursday) or (date_to_check == penultimate_thursday)

def getExpPrefNifty(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisThursday = inDate + relativedelta(weekday=TH(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    if isLastThursday(thisThursday):
        #Doesn't matter if thursday is a holiday. Its going to be a monthly expiry anyway
        return f'NIFTY{monthExp(thisThursday)}' 
    else: 
        expDay = thisThursday
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'NIFTY{normExp(expDay)}'


def getExpPrefBankNifty(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    thisThursday = inDate + relativedelta(weekday=TH(0))
    #Is this Thursday is the last thursday of the month 
    #Or is today the penultimate Thursday of the month
    #Remember Remember, the 21st of September
    #If yes, its a monthly expiry
    if isLastThursday(thisThursday) or isPenUltimateThursday(inDate):
        #Doesn't matter if thursday is a holiday. Its going to be a monthly expiry anyway
        return f'BANKNIFTY{monthExp(thisThursday)}'
    else:
        #Else a weekly expiry, with wednesday as the expiry 
        expDay = inDate + relativedelta(weekday=WE(0)) #This wednesday
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'BANKNIFTY{normExp(expDay)}'
