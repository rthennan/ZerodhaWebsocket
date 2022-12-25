# -*- coding: utf-8 -*-
"""
Created on Sun Dec 25 23:02:20 2022

@author: Rajesh
"""

import pandas as pd
from datetime import datetime as dt

#To convert 'January 26, 2023' to '2023-01-26'
def dater(inStr):
    return dt.strptime(inStr, '%B %d, %Y')
    

hols = pd.read_excel("tradeHoliday.xlsx")
tradingHolidays=hols.copy(deep=True)
tradingHolidays['Date'] = tradingHolidays['Date'].apply(dater)
tradingHolidays['Date'].to_csv('tradingHolidays.csv', index=False)
