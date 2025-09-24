import pandas as pd
import calendar
from datetime import datetime as dt,timedelta as tdel, date
from dateutil.relativedelta import relativedelta, TH, WE
"""
This is how DAS was caculating expiry Prefixes till March 2024.
But new version since March 2024 doesn't rely on this anymore.
Now useful for getting the prefix and in turn Table name for backtesting

Expiry day changes for BankNifty Options:
    - Banknifty weekly expiry day changed to Wednesday w.e.f the 4th of September 2024
      https://zerodha.com/marketintel/bulletin/358889/revision-in-expiry-day-for-banknifty-weekly-options-contracts

    - Banknifty monthly and quartely expiry day changed to Wednesday w.e.f  1st of March 2024
      https://zerodha.com/marketintel/bulletin/367671/revision-in-expiry-day-of-monthly-and-quarterly-banknifty-fo-contracts
      
     - BankNifty expiries are now only monthly  - https://www.angelone.in/blog/bank-nifty-weekly-expiry-bids-adieu-2
     - Nov 13 2024

Expiry Day changed for Nifty from the 29th of August 2025
- Until 28th August 2025 → Thursday was expiry.
- From 2nd September 2025 onwards → Tuesday is expiry.
https://zerodha.com/marketintel/bulletin/417370/revision-in-expiry-day-of-index-and-stock-derivatives-contracts

BankNifty expiry changes:
    https://hdfcsky.com/blogs/share-market/bank-nifty-expiry
    Not adapted
    Track this Manually please.
    I am tired of these changes in BankNifty
    
    I think BankNifty expiry is still based on Last Thursday.
    Not fixing this. May be for later.
    Bug me if you need this or raise a PR
    
    October 2020: Quarterly Bank Nifty futures contracts were introduced, expiring on the last Thursday of the March, June, September, and December cycle.
    September 2023: The NSE shifted the weekly expiry of Bank Nifty from Thursday to Wednesday.
    November 2024: Weekly expiry contracts for Bank Nifty were discontinued on November 20, 2024.
    January 2025: The monthly and quarterly expiry for Bank Nifty shifted from Wednesday to Thursday.
    March 2025: The monthly and quarterly expiry for Bank Nifty shifted from Last Thursday to Monday.

"""

#trade holidays Path
holsFilePath = 'tradingHolidaysAllYears.csv'
hols = pd.read_csv(holsFilePath)
holidays = hols['Date'].values.tolist()
holidayDates = [dt.strptime(str(x), '%Y-%m-%d').date() for x in holidays]
yearsinMainHolidayList = list(set([str(d.year) for d in holidayDates]))

#Weekly expiry
def normExp(inDate3):
    if inDate3.month < 10:
        return str(inDate3.year)[2:]+str(inDate3.month)+('0'+str(inDate3.day))[-2:]
    elif 10 <= inDate3.month <= 12:
        return str(inDate3.year)[2:]+(str(calendar.month_name[inDate3.month]).upper()[0])+('0'+str(inDate3.day))[-2:]

#Monthly Expiry
def monthExp(inDate3):
    inDate3 = dt.strptime(str(inDate3), '%Y-%m-%d').date()
    return (str(inDate3.year)[2:])+(str(calendar.month_name[inDate3.month]).upper()[:3])


def isLastWeekday(date_to_check, target_weekday):
    """Generic check: is this the last target_weekday of the month?"""
    year, month = date_to_check.year, date_to_check.month
    last_day = calendar.monthrange(year, month)[1]
    last_candidate = date(year, month, last_day)

    while last_candidate.weekday() != target_weekday:
        last_candidate -= tdel(days=1)

    return date_to_check == last_candidate


def getExpPrefNifty(inDate):
    """
    Get NIFTY expiry prefix (weekly or monthly).
    
    - Until 28th Aug 2025 → Thursday expiry
    - From 2nd Sep 2025 → Tuesday expiry
    - If weekly expiry falls on holiday → roll back
    - Monthly expiry always last expiry-day of the month (holiday or not)
    """
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  

    if str(inDate.year) not in yearsinMainHolidayList:
        print(f"getExpiryPrefix : Given date {inDate} doesn't seem to be covered by {holsFilePath}\nYears in the holiday List - {yearsinMainHolidayList}")
        return None

    last_thursday_expiry = date(2025, 8, 28)   # last Thursday expiry
    
    #Everything After last_thursday_expiry is a Tuesday Expiry
    if inDate <= last_thursday_expiry:
        # Thursday expiry regime
        this_expiry_day = inDate + relativedelta(weekday=TH(0))
        expiry_weekday = calendar.THURSDAY
    else:
        # Tuesday expiry regime
        this_expiry_day = inDate + relativedelta(weekday=calendar.TUESDAY)
        expiry_weekday = calendar.TUESDAY

    # Monthly expiry check → last expiry weekday of the month
    if isLastWeekday(this_expiry_day, expiry_weekday):
        return f'NIFTY{monthExp(this_expiry_day)}'
    else:
        expDay = this_expiry_day
        # For weekly expiry, roll back if holiday
        while str(expDay) in holidays:
            expDay -= tdel(days=1)
        return f'NIFTY{normExp(expDay)}'



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


#the good old days before September 4, 2023 When all expiries were Thursday
def getExpPrefBankNiftyThursday(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisThursday = inDate + relativedelta(weekday=TH(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    if isLastWeekday(thisThursday, calendar.THURSDAY):
        #Doesn't matter if thursday is a holiday. Its going to be a monthly expiry anyway
        return f'BANKNIFTY{monthExp(thisThursday)}' 
    else: 
        expDay = thisThursday
        #if date is a holiday, keep decrementing till a trading day is found
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'BANKNIFTY{normExp(expDay)}'    

#Sep 4 2023 to March 2024 - Weekly expiry wednesday. Monthly and qtly - Thursday
def getExpPrefBankNiftyWierdo(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    thisThursday = inDate + relativedelta(weekday=TH(0))
    #Is this Thursday the last thursday of the month 
    #Or is today the penultimate Thursday of the month
    #Remember Remember, the 2nd of September 2023
    #If yes, its a monthly expiry
    if isLastWeekday(thisThursday, calendar.THURSDAY) or isPenUltimateThursday(inDate):
        #Doesn't matter if thursday is a holiday. Its going to be a monthly expiry anyway
        return f'BANKNIFTY{monthExp(thisThursday)}'
    else:
        #Else a weekly expiry, with wednesday as the expiry 
        expDay = inDate + relativedelta(weekday=WE(0)) #This wednesday
        #if date is a holiday, keep decrementing till a trading day is found
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'BANKNIFTY{normExp(expDay)}'
    
#From March 2024, both weekly and monthly contracts expire on Wednesday
def getExpPrefBankNiftyWednesday(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisWednesday = inDate + relativedelta(weekday=WE(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    if isLastWeekday(thisWednesday, calendar.WEDNESDAY):
        #Doesn't matter if wednesday is a holiday. 
        #Its going to be a monthly expiry anyway. Instrument name won't change
        return f'BANKNIFTY{monthExp(thisWednesday)}' 
    else: 
        expDay = thisWednesday
        #if date is a holiday, keep decrementing till a trading day is found
        while str(expDay) in holidays:
            expDay = expDay - tdel(days=1)
        return f'BANKNIFTY{normExp(thisWednesday)}'
    
#From Nov 13 2024, no more weekly expiries for Banknifty
def getExpPrefBankNiftyMonthlyOnly(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()  
    thisWednesday = inDate + relativedelta(weekday=WE(0))
    #Is this Thursday the last thursday of the month?
    #If yes, its a monthly expiry
    #Doesn't matter if wednesday is a holiday. 
    #Its going to be a monthly expiry anyway. Instrument name won't change
    return f'BANKNIFTY{monthExp(thisWednesday)}' 
  
    
def getExpPrefBankNifty(inDate):
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()
    sepChangeDate = date(2023, 9, 4)
    marChangeDate = date(2024, 3, 1)
    novChangeDate = date(2024, 11, 13)
    # Ensure the input date's year is covered in the holidays file
    if str(inDate.year) in yearsinMainHolidayList:
        # If inDate is before the first change date (4th September 2023)
        if inDate < sepChangeDate:
            return getExpPrefBankNiftyThursday(inDate)
        # If inDate is between the first and second change dates
        elif sepChangeDate <= inDate < marChangeDate:
            return getExpPrefBankNiftyWierdo(inDate)
        # If inDate is after the second change date (1st March 2024) But before Nov 13, 2024
        elif marChangeDate <= inDate <= novChangeDate:
            return getExpPrefBankNiftyWednesday(inDate)
        elif inDate > novChangeDate:
            return getExpPrefBankNiftyMonthlyOnly(inDate)
    else:
        print(f"getExpiryPrefix : Given date {inDate} doesn't seem to be covered by {holsFilePath}\nYears in the holiday List - {yearsinMainHolidayList}")

if __name__=='__main__':
    # Example usage
    inDate = '2020-01-01' # Use appropriate date format as a string
    print(getExpPrefBankNifty(inDate))
    print(getExpPrefNifty(inDate))

