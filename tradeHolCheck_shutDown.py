"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Check if today is a trading Holiday. Notify and shut the machine down if trading holiday.
Added as a cronjob to run at 08:40 a.m., Monday to Friday: 38 8 * * 1-5 /usr/bin/python3 /home/ubuntu/ZerodhaWebsocket/sysStartupNotify.py
"""

from datetime import datetime as dt, date
from time import sleep
from os import path, makedirs, system
import sys

#Expects DAS_gmailer and tradeHolidayCheck to be in the same path 
# Get the absolute path of the current file
scriptAbsolutePath = path.abspath(__file__)
#Get Directory
# Get the directory of the current script
scriptDirectory = path.dirname(scriptAbsolutePath)

# Append the script directory to the system path
if scriptDirectory not in sys.path:
    sys.path.append(scriptDirectory)

# Allows importing DAS_gmailer and tradeHolidayCheck irrespective of where traceHolCheck is called from 
from DAS_gmailer import DAS_mailer
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
		
