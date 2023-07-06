import pandas as pd
import calendar
from datetime import datetime as dt,timedelta as tdel
from dateutil.relativedelta import relativedelta, TH, FR
from os import path

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


#today = dt.today().date()
#today = dt.strptime('2023-07-07', '%Y-%m-%d').date()

def getExpPref(indexName, inDate):
    pass
    ##Leave this block as is, in case NSE tries another such genius move
    #expChangeDate = dt.strptime('2023-07-07', '%Y-%m-%d').date()
    #if today < expChangeDate:
        #expDay = today + relativedelta(weekday=TH(0))
    #elif today == expChangeDate:
        #expDay = today + relativedelta(weekday=FR(0), weeks=1)
    #else:
        #expDay = today + relativedelta(weekday=FR(0))
    inDate = dt.strptime(str(inDate), '%Y-%m-%d').date()   
    expDay = inDate + relativedelta(weekday=TH(0))    
    while str(expDay) in holidays:
        expDay = expDay - tdel(days=1)
    #if the expDay falls in the next month, assume this is normal expiry
    if expDay.month != inDate.month:
        expiryPrefix = indexName+normExp(expDay)
    else:
        next_week = expDay + relativedelta(weeks=1)
        #Find the date for the same day next week and compare the months.
        #Same month? not last week. Different month? last week
        if next_week.month == expDay.month:
            #Not the last day of week for the month
            expiryPrefix = indexName+normExp(expDay)
        else:
            expiryPrefix = indexName+monthExp(expDay)
    return expiryPrefix            


        
    



