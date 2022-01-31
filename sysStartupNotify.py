# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 21:53:51 2019

@author: Thennan
"""

import datetime
import sys
from datetime import datetime as dt
import threading
import json
import os
import smtplib

with open('creds.json','r') as credsFile:
    creds = json.load(credsFile)

senderEmailAddress = creds['senderEmailAddress']
senderEmailPass = creds['senderEmailPass']
destinationEmailAddress = creds['destinationEmailAddress']

def mailerThr(recipient, subject, body):
    thredMail = threading.Thread(target=mailerActual,args=(recipient,subject,body,))
    thredMail.start()  

def log(txt):

	directory = 'startUpLogs'
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = directory+'/'+str(datetime.date.today())+'_mailer.log'
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
	with open(logFile,'a') as f:
		f.write(logMsg)

def mailerActual(recipient, subject, body):
    
    pwd = senderEmailPass
    FROM = senderEmailAddress
    user = FROM
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject + " " + str(datetime.date.today())
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
        msg = "Mail with subject '" + SUBJECT + "' sent Succesfully to "+ recipient
        print(msg)
        log(msg)
    except Exception as e:
        msg = 'Exception : '+str(e)
        lineNoMailException =sys.exc_info()[-1].tb_lineno
        print(lineNoMailException)
        print(msg)
        log(lineNoMailException)
        log(msg)
        
mailerThr(destinationEmailAddress,'AWS1- Started Successfully','AWS1- Started Successfully at '+str(dt.now().replace(microsecond=0)))
log('AWS1- Started Successfully at '+str(dt.now().replace(microsecond=0)))