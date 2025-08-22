"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

getHolidayListFromNSE based on https://github.com/tahseenjamal/nse_holidays

Install Chrome in Linux 
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb

Version
google-chrome --version
Tested in version => Google Chrome 123.0.6312.58

Get Holiday List => getHolidayListFromUpStox (Free and Open). 
If fail, getHolidayListFromNSE. 
If Fail, use the local file.
If not local file, play it safe and say today is NOT a holiday.
Every time getHolidayListFromUpStox or getHolidayListFromNSE is successful, the holiday list is stored locally as tradingHolidays.csv
Can be Run standalone - Checks if today is a holiday
Return True if the given date is found in the holiday list. Else False.

"""
import pandas as pd
from datetime import datetime as dt, date, timedelta
from os import path, makedirs
from selenium import webdriver #pip install selenium==4.6 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
from DAS_errorLogger import DAS_errorLogger
import traceback
import requests
numbOfRetries = 5

from DAS_gmailer import DAS_mailer

def holidayCheckLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_tradeHolCheck_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + txt
    with open(logFile,'a') as f:
        f.write(logMsg)
    
def getHolidayListFromUpStox():
    upStoxEndPoint = 'https://api.upstox.com/v2/market/holidays'
    upStoxHolidayList = []
    for attempt in range(1, numbOfRetries+1):
        try:
            upStoxResponse = requests.get(upStoxEndPoint)
            if upStoxResponse.status_code != 200:
                raise Exception(f"getHolidayListFromUpStox from {upStoxEndPoint} Failed. HTTP Response => {upStoxResponse.status_code}")
            
            holidayAPI_Response = upStoxResponse.json()
            if holidayAPI_Response.get('status') != 'success':
                raise Exception(f"API response status not success: {holidayAPI_Response.get('status')}")
            
            holidaysListFromUpstox = holidayAPI_Response.get('data', [])
            # Looking for NSE holidays only
            for holidayItem in holidaysListFromUpstox:
                closed_exchanges = holidayItem.get('closed_exchanges', [])
                if 'NSE' in closed_exchanges:
                    upStoxHolidayList.append(holidayItem['date'])
            
            tradingHolidays = pd.DataFrame(upStoxHolidayList, columns=['Date'])
            tradingHolidays.to_csv('tradingHolidays.csv', index=False)
            
            msg = 'Successfully fetched trading holiday list from Upstox and saved it Locally'
            holidayCheckLogger(msg)
            return upStoxHolidayList

        except Exception as e:
            msg = f'getHolidayListFromUpStox Failed. Attempt No : {attempt}. Exception -> {e} Traceback : {traceback.format_exc()}.\nWill retry after 30 seconds'
            holidayCheckLogger(msg)
            DAS_errorLogger('tradeHolidayCheck - ' + msg)
            sleep(30)
        else:
            break
    else:
        msg = f'getHolidayListFromUpStox - Failed After {numbOfRetries} attempts. Will try getHolidayListFromNSE'
        holidayCheckLogger(msg)
        DAS_errorLogger('tradeHolidayCheck - ' + msg)
        DAS_mailer('DAS - getHolidayListFromUpstox Failed.', msg)
        return []


def getHolidayListFromNSE():
    for attempt in range(1,numbOfRetries+1):
        try:    
            nseHolidayListurl = 'https://www.nseindia.com/resources/exchange-communication-holidays'
            options = Options()
            options.headless = True
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
            options.add_argument('window-size=1920x1080')
            # Use Service object to specify path to the Chrome driver
            service = Service(ChromeDriverManager().install())
            #driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)
            # Initiate the webdriver instance with the service and options
            driver = webdriver.Chrome(service=service, options=options)    
            driver.get(nseHolidayListurl)    
            # Wait for the initial page elements to load
            WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "holidayTable")))
            
            # Now, wait for the JavaScript condition: Check if the table is present and has at least one row
            wait_time = 0
            max_wait = 30  # Maximum time to wait in seconds
            while wait_time < max_wait:
                # Check if the holiday table exists and has at least one row
                is_table_populated = driver.execute_script("""
                    var table = document.getElementById('holidayTable');
                    if (table && table.getElementsByTagName('tr').length > 1) {
                        return true;
                    }
                    return false;
                """)
                if is_table_populated:
                    holidayCheckLogger('Table is loaded and populated.')
                    break
                sleep(1)  # Wait for a second before checking again
                wait_time += 1

            page_content = driver.page_source
            holidaysDF = pd.read_html(page_content, attrs={'id': 'holidayTable'})[0]
            driver.close()
            
            #Convert the dates into yyyy-mm-dd format
            holidaysDF['Date'] = holidaysDF['Date'].apply(lambda x: dt.strptime(x.strip(), '%d-%b-%Y').strftime('%Y-%m-%d'))
            #saving successfull list as as a fallback - tradingHolidays.csv
            #This will be used in case getHolidayListFromNSE fails
            tradingHolidays = holidaysDF['Date']
            tradingHolidays.to_csv('tradingHolidays.csv', index=False) 
            msg = 'Successfully fetched trading holiday list from the NSE site and saved it Locally'
            holidayCheckLogger(msg)
            return  tradingHolidays.to_list()    
        except Exception as e:
            msg = f'getHolidayListFromNSE Failed. Attempt No :{attempt} . Exception-> {e} Traceback : {traceback.format_exc()}.\nWill retry after 30 seconds'
            holidayCheckLogger(msg)
            DAS_errorLogger('tradeHolidayCheck - '+msg)
            sleep(30)
        else:
            break
    else:
        msg = f'getHolidayListFromNSE Failed After {numbOfRetries} attempts. Will try using old file'
        holidayCheckLogger(msg)
        DAS_errorLogger('tradeHolidayCheck - '+msg)
        DAS_mailer('DAS - getHolidayListFromNSE Failed.',msg)   
        return []

def getHolidayList():
    tradeHolidayList = getHolidayListFromUpStox()
    if len(tradeHolidayList)>0:
        return tradeHolidayList
    else: 
        tradeHolidayList = getHolidayListFromNSE() 
    if len(tradeHolidayList)>0:
        return tradeHolidayList
    else:
        msg = 'getHolidayListFromUpStox and getHolidayListFromNSE failed. Using Local file'
        holidayCheckLogger(msg)
        DAS_errorLogger('tradeHolidayCheck - '+msg)
        try:
            if path.exists('tradingHolidays.csv'):
                tradingHolidays = pd.read_csv('tradingHolidays.csv')['Date'].to_list()
                return tradingHolidays
            else:
                msg = 'getHolidayListFromNSE failed. tradingHolidays.csv not found. Returning empty list'
                holidayCheckLogger(msg)
                DAS_mailer('DAS - getHolidayListFromNSE Failed',msg)
                DAS_errorLogger('tradeHolidayCheck - '+msg)
                #Returning an empty list . This will always say today is not a trading holiday
                return []
        except Exception as e2:
            msg = f' Fall Back failed with exception {e2} Traceback : {traceback.format_exc()}. Returning empty list'
            holidayCheckLogger(msg)
            DAS_errorLogger('tradeHolidayCheck - '+msg)
            DAS_mailer('DAS - getHolidayList Failed',msg)
            #Returning an empty list . This will always say today is not a trading holiday
            return []   
#Will return True only if the input date is a trading holiday
def tradeHolidayCheck(inDate):
    #Double conversion to avoid type mismatch
    inDateString = str(inDate)
    # Convert string to date object
    dateObj = dt.strptime(inDateString, '%Y-%m-%d').date()
    # Check if the date is a Saturday or Sunday
    if dateObj.weekday() in (5, 6):
        msg = f'{inDate} is a trading holiday (Weekend). Exit'
        holidayCheckLogger(msg)
        return True
    
    inDate = inDateString
    tradeHolsFilePath = 'tradingHolidays.csv'
    oneHourAgo = dt.now() - timedelta(hours=1)
    #If the tradingholiday file exists and is fresh (not older than one hour, use it)
    if path.exists(tradeHolsFilePath):
        holidayListModifiedTime = dt.fromtimestamp(path.getmtime(tradeHolsFilePath))
        if holidayListModifiedTime >= oneHourAgo:
            msg = 'local tradingHolidays.csv is fresh. Using it.'
            holidayCheckLogger(msg)
            tradingHolidayList = pd.read_csv(tradeHolsFilePath)['Date'].to_list()
        else:
            msg = 'local tradingHolidays.csv is older than 1 hour. Downloading latest list.'
            holidayCheckLogger(msg)
            tradingHolidayList = getHolidayList()
    else:
        msg = 'Fresh tradingHolidays.csv file not found locally. Downloading latest list.'
        holidayCheckLogger(msg)
        tradingHolidayList = getHolidayList()

    if inDate in tradingHolidayList:
        msg = f'{inDate} is a trading holiday. Exit'
        holidayCheckLogger(msg)
        return True
    else:
        msg = f'{inDate} is NOT a trading holiday. Holiday check passed. Will continue.'
        holidayCheckLogger(msg)
        return False
		
if __name__ == '__main__':
    tradeHolidayCheck(date.today())