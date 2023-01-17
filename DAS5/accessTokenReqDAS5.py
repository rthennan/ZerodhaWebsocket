# -*- coding: utf-8 -*-
"""
Change Log:
    16 July 2021 - added new token fetch code

@author: Thennan
Chrome version  - 85.0.4183.83-1
https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_85.0.4183.83-1_amd64.deb

wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_85.0.4183.83-1_amd64.deb \
  && sudo apt install -y /tmp/chrome.deb \
  && rm /tmp/chrome.deb
"""
import time
import os
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from kiteconnect import KiteConnect
import MySQLdb
from sendMailV1 import mailer as mail
from webdriver_manager.chrome import ChromeDriverManager
import pyotp
import json

credsFile = os.path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

destinationEmailAddress = creds['destinationEmailAddress']
ZerodhaLoginName = creds['ZerodhaLoginName']
ZerodhaPass = creds['ZerodhaPass']
apiKey1 = creds['apiKey1']
apisec1 = creds['apisec1']
mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
TOTP_pin = creds['TOTP']
#If user had added a 2FA pin, it will be used as is.
#Else will be generating a totp using the provided totp secret
if len(TOTP_pin)> 10:
    usingTOTP = True
else:
    usingTOTP = False


def log(txt):
    directory = os.path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
    if not os.path.exists(directory):
        os.makedirs(directory)
    logFile = os.path.join(directory,str(datetime.date.today())+'_accessToken.log')
    logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)

numbOfRetries = 5
for attempt in range(1,numbOfRetries+1):
	
	try:

	    conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
	    conn.autocommit(True)
	    c = conn.cursor()
	    c.execute("create DATABASE if not exists aws_tokens")
	    c.execute("create table if not exists aws_tokens.das5 (time DATETIME UNIQUE,requestUrl varchar(255) ,reqToken varchar(255) ,accessToken varchar(255))")
	    shortsql = "INSERT into aws_tokens.das5 values (%s, %s, %s, %s)"
	    """Using DAS5 App"""
	    apikey = apiKey1
	    apisec = apisec1
	    """Using DAS5 App"""
	    kite = KiteConnect(api_key = apikey)
	    url = (kite.login_url())
	    loginName = ZerodhaLoginName
	    password = ZerodhaPass

	    options = Options()
	    options.headless = True
	    driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)

	    log("DAS5 - Access Token - Execution started")
	    print("DAS5 - Access Token - Execution started")

	    driver.get(url)
	    log("DAS5 - Entered Try Block")
	    "DAS5 - Access Token - Entered Try Block"

	    #Wait for the Page to Load completely
	    print("Opening the main Login Page")
	    time.sleep(10)
	    #Enter credentials and submit
	    driver.find_element_by_xpath('//*[@id="container"]/div/div/div[2]/form/div[1]/input').send_keys(loginName)
	    driver.find_element_by_xpath('//*[@id="container"]/div/div/div[2]/form/div[2]/input').send_keys(password)
	    driver.find_element_by_xpath('//*[@id="container"]/div/div/div/form/div[4]/button').click()
	    print("Credentials Entered and submitted. Waiting for TOTP page to load")
	    #Wait for the 2FA Page to Load completely
	    time.sleep(10)
	    #Enter OTP and click submit


	    if usingTOTP:
            totp = pyotp.TOTP(TOTP_pin)
            otpchangers = [29,30,31,59,0,1]
                #Waiting if OTP is about to change
            while datetime.datetime.now().second in otpchangers:
                log('otpchanger '+str(datetime.datetime.now().second))
                time.sleep(1)
                #Enter TOTP
		   driver.find_element_by_xpath('//*[@id="container"]/div[1]/div/div/form/div[2]/input').send_keys(totp.now())
	    else:
            #Enter Pin
           driver.find_element_by_xpath('//*[@id="container"]/div[1]/div/div/form/div[2]/input').send_keys(TOTP_pin) #Changed on 2022-09-26 

	    #Wait for the 2FA Page to Load completely
	    print("DAS5 - Pin entered and submitted.")
	    time.sleep(10)
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
	    print(url)
	    print(tok)
	    log(url)
	    log(tok)
	    print("Retrieving Access Token")
	    session = kite.generate_session(reqToken, apisec)
	    accessToken = session['access_token']
	    msg = "Access Token: "+accessToken
	    print(msg)
	    log(msg)
	    c.execute(shortsql,[datetime.datetime.now(),tokenUrl,reqToken,accessToken])
	    c.close()
	    conn.close()
	    log('Updated in DB')
	    print('Updated in DB')
	    msg = f'DAS5: Access Token Successful after {attempt} attempts'
	    log(msg)
	    print(msg)
	    mail(destinationEmailAddress,msg,'DAS5: Access Token succeeded at '+str(datetime.datetime.now())+'\n Proceeding to Instrument List file lookup')

	except Exception as e:
		msg = 'DAS5 - Access token Failed. Attempt No :'+str(attempt)+' Exception-> ' + str(e)+' Will retry after 30 seconds'
		log(msg)
		print(msg)
		time.sleep(30)
	else:
        break
else:
    msg = 'DAS5 - Access token Failed After '+str(numbOfRetries)+' attempts.'
    log(msg)
    mail(destinationEmailAddress, 'DAS5 - Access token Failed.',msg)      	