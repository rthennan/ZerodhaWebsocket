"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Install Chrome in Linux 
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb

Version
google-chrome --version
Tested in version => Google Chrome 123.0.6312.58

Gets the access token for the Zerodha API app and stores it in {accessTokenDBName}.kite1tokens
Can be Run standalone - Updates latest accessToken in DB
Returns True if success. Else False.

isAccessTokenInDBFresh
If the automated process fails for whatever reason, the code checks if the Access Token in the DB is Fresh 
(Created after 08:00 the same day)
https://kite.trade/forum/discussion/7759/access-token-validity
And returns True if the token is Fresh
This way, We are good if
    - The accesstokenreq code fails after storing the access token in the DB
    - accesstokenreq failed, but the code was generated manually using manualAccessTokenReq or some other way
- Why not check if the token in the DB is fresh, even before trying to get one automatically?
- Allows the code to try at least once.

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

numbOfRetries = 5
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

def accessTokenLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_accessToken_Logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

def isAccessTokenInDBFresh():
    #Get latest access token's timestamp from DB
    conne = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass, db=accessTokenDBName, port=mysqlPort)
    ce = conne.cursor()
    ce.execute('select timestamp from kite1tokens order by timestamp desc limit 1')
    accTokenLatestTimeStamp = str(ce.fetchone()[0])
    ce.close()
    conne.close()  
    # Parse the string to a datetime object
    accTokenLatestTimeStamp = dt.strptime(accTokenLatestTimeStamp, '%Y-%m-%d %H:%M:%S')
    
    # Create a datetime object for today at 08:00 a.m.
    # Replace the hour, minute, second, and microsecond to get today at 08:00 a.m.
    today8AM = dt.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    #Was accessToken generated after 08:00 today?
    return accTokenLatestTimeStamp > today8AM
    

def accessTokenReq():    
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
            kite = KiteConnect(api_key = apiKey)
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
            exceptMsg = msg = f'DAS - Access token Failed. Attempt No :{attempt} . Exception-> {e}. Traceback : {traceback.format_exc()}.\nWill check if accessToken in DB is fresh'
            DAS_errorLogger(msg)
            accessTokenLogger(msg)
            availableTokenGood = isAccessTokenInDBFresh()
            if availableTokenGood:
                msg = 'Access token available in DB is Fresh. Will use it for the ticker.\n But see why accessTokenReq failed in the first place'
                DAS_errorLogger(msg)
                accessTokenLogger(msg) 
                DAS_mailer('DAS - accessTokenReq FAILED!!!. Using latest token from Today',f'Check DAS_accessToken_Logs_{str(date.today())}.log to see why it failed and troubleshoot if the issue is not transient')
                return True
            else:
                msg = '\nAccess token in DB is not fresh.\nRun manualAccessTokenReq.py if possible.\nWill retry accessTokenReq in 30 seconds'
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