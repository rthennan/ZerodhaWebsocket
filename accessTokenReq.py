"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan

Install Chrome in Linux 
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb

Version
google-chrome --version
Tested in version => Google Chrome 123.0.6312.58

"""
import time
from datetime import datetime as dt, date
from selenium import webdriver #pip install selenium==4.6 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from kiteconnect import KiteConnect # pip install kiteconnect==5.0.1
import MySQLdb #sudo apt-get install python3-mysqldb
from DAS_gmailer import DAS_mailer
from webdriver_manager.chrome import ChromeDriverManager #pip install webdriver_manager==4.0.1
import pyotp #pip install pyotp
import json
from os import path, makedirs
from DAS_errorLogger import DAS_errorLogger
import traceback


def accessTokenLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_accessToken_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

numbOfRetries = 5
def accessTokenReq():
    configFile = 'dasConfig.json'
    with open(configFile,'r') as configFile:
        dasConfig = json.load(configFile)
    
    zerodhaLoginName = dasConfig['ZerodhaLoginName']
    zerodhaPass = dasConfig['ZerodhaPass']
    apiKey = dasConfig['apiKey']
    apisec = dasConfig['apisec']
    mysqlHost = dasConfig['mysqlHost']
    mysqlUser = dasConfig['mysqlUser']
    mysqlPass = dasConfig['mysqlPass']
    mysqlPort = dasConfig['mysqlPort']
    TOTP_seed = dasConfig['TOTP_seed']
    accessTokenDBName = dasConfig['accessTokenDBName']
    
    exceptMsg = ''
    for attempt in range(1,numbOfRetries+1):
    
        try:
    
            conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, port=mysqlPort)
            conn.autocommit(True)
            c = conn.cursor()
            c.execute(f"CREATE DATABASE IF NOT EXISTS {accessTokenDBName}")
            #Why kite1tokens ? If zerodha imposes limits on the number of subscribable instruments in the fture, might need more API apps
            c.execute(f"CREATE TABLE IF NOT EXISTS {accessTokenDBName}.kite1tokens (timestamp DATETIME UNIQUE,requestUrl varchar(255) ,reqToken varchar(255) ,accessToken varchar(255))")
            shortsql = f"INSERT into {accessTokenDBName}.kite1tokens values (%s, %s, %s, %s)"
            """Using DAS1 App"""
            apikey = apiKey
            apisec = apisec
            """Using DAS1 App"""
            kite = KiteConnect(api_key = apikey)
            url = (kite.login_url())
            loginName = zerodhaLoginName
            password = zerodhaPass
            
            options = Options()
            options.headless = True
            # Use Service object to specify path to the Chrome driver
            service = Service(ChromeDriverManager().install())
            #driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)
            # Initiate the webdriver instance with the service and options
            driver = webdriver.Chrome(service=service, options=options)
            
            accessTokenLogger("DAS - Access Token - Execution started")
            
            driver.get(url)
            accessTokenLogger("DAS - Entered Try Block")
                    
            #Wait for the Page to Load completely
            wait = WebDriverWait(driver, 10)
            accessTokenLogger("Opening the main Login Page")
            #Enter credentials and submit
            submitButton = '//*[@id="container"]/div/div/div/form/div[4]/button'
    
            element = wait.until(EC.element_to_be_clickable((By.XPATH, submitButton))) 
            
            driver.find_element(By.XPATH,'//*[@id="container"]/div/div/div[2]/form/div[1]/input').send_keys(loginName)
            driver.find_element(By.XPATH,'//*[@id="container"]/div/div/div[2]/form/div[2]/input').send_keys(password)
            driver.find_element(By.XPATH,submitButton).click()
            accessTokenLogger("Credentials Entered and submitted. Waiting for TOTP page to load")
            #Wait for the 2FA Page to Load completely
    
            totpInputXpath = '//*[@id="container"]/div[2]/div/div[2]/form/div[1]/input'
            # Wait for the totp field to load
            element = wait.until(EC.element_to_be_clickable((By.XPATH, totpInputXpath))) 
            
            totp = pyotp.TOTP(TOTP_seed)
            otpchangers = [29,30,31,59,0,1]
            #Waiting if OTP is about to change
            while dt.now().second in otpchangers:
                accessTokenLogger('otpchanger '+str(dt.now().second))
                time.sleep(1)
                #Enter TOTP
            driver.find_element(By.XPATH,totpInputXpath).send_keys(totp.now())
            #Wait for the 2FA Page to Load completely
            accessTokenLogger("DAS - Pin entered and submitted.")
            time.sleep(5)
            #Capture the redirect URL
            tokenUrl = (driver.current_url)
            reqToken = tokenUrl
            #Token fetch code start
            
            lenReq = len("request_token=")
            reqToken = reqToken[reqToken.find('request_token=')+lenReq:]
            endChar = reqToken.find('&')
            if endChar!=-1:
                reqToken = reqToken[:endChar]
            #Token fetch code end
            url = "Response URL: " +tokenUrl
            tok = "Request Token: " +reqToken
            accessTokenLogger(url)
            accessTokenLogger(tok)
            accessTokenLogger("Retrieving Access Token")
            session = kite.generate_session(reqToken, apisec)
            accessToken = session['access_token']
            msg = f"Access Token: {accessToken}"
            accessTokenLogger(msg)
            c.execute(shortsql,[dt.now(),tokenUrl,reqToken,accessToken])
            c.close()
            conn.close()
            accessTokenLogger('Updated in DB')
            msg = f'Access Token succeeded at {dt.now()}'
            accessTokenLogger(msg)
            #DAS_mailer(f'DAS - Access Token Successful after {attempt} attempt(s)' ,msg)
            return True
    
        except Exception as e:
            exceptMsg = e
            msg = f'DAS - Access token Failed. Attempt No :{attempt} . Exception-> {e}. Traceback : {traceback.format_exc()}.\nWill retry after 30 seconds'
            DAS_errorLogger(msg)
            accessTokenLogger(msg)
            time.sleep(30)
        else:
            break
    else:
        msg = f'DAS - Access token Failed After {numbOfRetries} attempts. Exception: (exceptMsg)'
        accessTokenLogger(msg)
        DAS_errorLogger(msg)
        DAS_mailer('DAS - Access token Failed.',msg) 
        return False

if __name__ == '__main__':
    accessTokenReq()