import datetime
from sendMailV1 import mailer as mail
import json

credsFile = os.path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)


destinationEmailAddress = creds['destinationEmailAddress']

def log(txt):
	import datetime
	import os
	directory = os.path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = os.path.join(directory, str(datetime.date.today())+'_DAS5Master.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg)

def DASfail(msg):
    print(msg)
    log(msg)
    mail(destinationEmailAddress,'DAS5 aborted',msg)

def DASpass(msg):
    print(msg)
    log(msg)
    mail(destinationEmailAddress,msg,msg+' '+str(datetime.date.today()))

    
