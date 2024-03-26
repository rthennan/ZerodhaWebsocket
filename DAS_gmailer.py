"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan
"""
from datetime import datetime as dt, date
import threading
import sys
from os import path,makedirs
import smtplib
import json
from DAS_errorLogger import DAS_errorLogger
import traceback


configFile = 'dasConfig.json'
with open(configFile,'r') as configFile:
    dasConfig = json.load(configFile)
recipientEmailAddress = dasConfig['destinationEmailAddress']
#Generate a list if multiple recipients mentioned
recipientEmailAddress = recipientEmailAddress.split(',')
senderEmailAddress = dasConfig['senderEmailAddress']
senderEmailPass = dasConfig['senderEmailPass']
#Gmail App password - https://support.google.com/mail/answer/185833?hl=en

# =============================================================================
# mail is not trigerred as a separate thread, the main code actually calling mailer for notification will have to wait for the mail to be sent.
# Hence instead of starting a new thread for mail in every code (I have used a lot of notifications), I have set the primary mailer to start
# as a separate thread
# =============================================================================

def mailLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        	makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_gmailer_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
    	f.write(logMsg)
        
def DAS_mailer(subject, body):
    try:
        thredMail = threading.Thread(target=mailerActual,args=(recipientEmailAddress,subject,body,))
        thredMail.start()
    except Exception as e:
        msg = f'send mail failed. Exception :{e}. Traceback : {traceback.format_exc()}'
        DAS_errorLogger('DAS_gmailer - '+msg)
        lineNoMailException =sys.exc_info()[-1].tb_lineno
        DAS_errorLogger('DAS_gmailer - '+lineNoMailException)
        mailLogger(msg)
        mailLogger(lineNoMailException)

def mailerActual(recipient, subject, body):
    pwd = senderEmailPass
    FROM = senderEmailAddress
    user = FROM
    TO = recipient
    SUBJECT = subject + " " + str(date.today())
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        msg = f'Mail with subject {SUBJECT} sent Succesfully to {recipient}'
        mailLogger(msg)
    except Exception as e:
        msg = f'Exception :{e}. Traceback : {traceback.format_exc()}'
        lineNoMailException =sys.exc_info()[-1].tb_lineno
        mailLogger(lineNoMailException)
        mailLogger(msg)
        DAS_errorLogger('DAS_gmailer - '+msg)