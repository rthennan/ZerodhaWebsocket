"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan
"""

from datetime import datetime as dt, date
from DAS_gmailer import DAS_mailer
from time import sleep
from os import path, makedirs, system
from tradeHolidayCheck import tradeHolidayCheck


def holidayCheckLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_mainLogs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_holidayCheckShutdown_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

todayDate =  str(date.today())
isTodayHoliday = tradeHolidayCheck(todayDate)
if isTodayHoliday:
    msg = todayDate + ' is a trading Holiday. I will not work. F**k off.'
    holidayCheckLogger('Shutting down :'+msg)
    DAS_mailer('DAS - Shutting down - Trading Holiday. ',msg)
    sleep(60) #To let threaded mail complete before shutting down
    system("sudo shutdown now -h")    
else:
    msg = todayDate + ' is NOT a trading Holiday. Holiday Check passed. DAS will continue'
    holidayCheckLogger(msg)
    DAS_mailer('DAS - Trading Day. Will continue further',msg)
		
