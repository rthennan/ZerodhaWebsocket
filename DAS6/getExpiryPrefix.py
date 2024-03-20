import pandas as pd
import calendar
from datetime import datetime as dt,timedelta as tdel, date
from dateutil.relativedelta import relativedelta, TH, WE
from os import path
"""
ChangeLog:
    21Sep2023:
        BankNifty weekly expiry day changed to Wednesday
        https://zerodha.com/marketintel/bulletin/358889/revision-in-expiry-day-for-banknifty-weekly-options-contracts
        
    20Mar2024
        BankNifty monthly expiry day changed to Wednesday
        https://zerodha.com/marketintel/bulletin/367671/revision-in-expiry-day-of-monthly-and-quarterly-banknifty-fo-contracts
        
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
    #This ins't actually the last thursday, can even be called last day.
    #But this variable will eventually hold the last thursday's date. Hence calling it so
    last_thursday = date(year, month, last_day)

    # Find the weekday index of the last Thursday
    while last_thursday.weekday() != calendar.THURSDAY:
        last_thursday -= tdel(days=1)

    # Check if the given date is the last Thursday
    return date_to_check == last_thursday

def isLastWednesday(date_to_check):
    date_to_check = dt.strptime(str(date_to_check), '%Y-%m-%d').date() 
    # Check if the given date is a Thursday (weekday index 3)
    if date_to_check.weekday() != calendar.WEDNESDAY:
        return False

    # Get the year and month from the given date
    year = date_to_check.year
    month = date_to_check.month

    # Find the last day of the month
    last_day = calendar.monthrange(year, month)[1]

    # Calculate the date for the last Wednesday of the month
    #This ins't actually the last Wednesday, can even be called last day.
    #But this variable will eventually hold the last wednesday's date. Hence calling it so
    last_wednesday = date(year, month, last_day)

    # Find the weekday index of the last Thursday
    while last_wednesday.weekday() != calendar.WEDNESDAY:
        last_wednesday -= tdel(days=1)

    # Check if the given date is the last Thursday
    return date_to_check == last_wednesday
    


def getExpPrefNifty(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisThursday = inDate + relativedelta(weekday=TH(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    if isLastThursday(thisThursday):
        #Doesn't matter if thursday is a holiday.
        #Its going to be a monthly expiry anyway. Instrument name won't change
        return f'NIFTY{monthExp(thisThursday)}' 
    else: 
        expDay = thisThursday
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'NIFTY{normExp(expDay)}'
    
#From March 2024, both weekly and monthly contracts expire on Wednesday
def getExpPrefBankNifty(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisWednesday = inDate + relativedelta(weekday=WE(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    if isLastWednesday(thisWednesday):
        #Doesn't matter if wednesday is a holiday. 
        #Its going to be a monthly expiry anyway. Instrument name won't change
        return f'BANKNIFTY{monthExp(thisWednesday)}' 
    else: 
        expDay = thisWednesday
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'BANKNIFTY{normExp(thisWednesday)}'    

#Was needed for the wierd state we were in, between 21Sep2023 and 01Mar2024
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

#Was needed for the wierd state we were in, between 21Sep2023 and 01Mar2024
def getExpPrefBankNifty_old(inDate):
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
    
    

