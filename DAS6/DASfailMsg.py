import datetime
from sendMailV1 import mailer as mail
import json
from os import path, makedirs

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

destinationEmailAddress = creds['destinationEmailAddress']

def log(txt):
	directory = path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
	if not path.exists(directory):
		makedirs(directory)
	logFile = path.join(directory,str(datetime.date.today())+'_DAS6Master.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg)

def DASfail(msg):
    print(msg)
    log(msg)
    mail(destinationEmailAddress,'DAS6 aborted',msg)

def DASpass(msg):
    print(msg)
    log(msg)
    mail(destinationEmailAddress,msg,msg+' '+str(datetime.date.today()))

    
