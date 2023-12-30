# -*- coding: utf-8 -*-
"""
Created on Sat Dec 30 13:01:26 2023

@author: Rajesh
"""

import pandas as pd
from datetime import datetime as dt
from os import path
import shutil

#To convert 'January 26, 2023' to '2023-01-26'
def stringDateToNum(inStr):
    return str(dt.strptime(inStr, '%B %d, %Y'))[:10]

def datetime64ToString(inStr):
    return dt.strptime(inStr, '%B %d, %Y')

newHolidayFilePath = path.join('lookup_tables','tradeHolidays.xlsx')
hols = pd.read_excel(newHolidayFilePath)
hols['Date'] = hols['Date'].apply(stringDateToNum)
holidaysFilePath = path.join('..','tradeHoliday','tradingHolidays.csv')
#Pushes the file to ../../tradeHoliday for main holiday checker cronjob. 
#Comment the below two lines if you don't want this.
hols['Date'].to_csv(holidaysFilePath, index=False) 
hols['Date'].to_csv(path.join('lookup_tables','tradingHolidays.csv'), index=False) #leaving a copy for reference in the local folder

holidays = hols['Date'].values.tolist()
#The table prefixes are based on the year for which the tradingHolidays have been provided.
#The year is fetched from the first entry in the tradingHolidays list

#Leaving a copy of the holiday list in original format in the tradeHolidays directory if needed
holYear = holidays[0][:4]
holFileName = f"tradeHolidays{holYear}.xlsx"
#Leaving a copy of the holidays xlsx file in the  ../../tradeHoliday folder 
#Comment the below two lines if you don't want this.
shutil.copy(newHolidayFilePath, path.join('..','tradeHoliday',holFileName))