from datetime import datetime as dt
import datetime
import time
from sendMailV1 import mailer as mail

def log(txt):
	import os
	directory = os.path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = os.path.join(directory,str(datetime.date.today())+'_DAS5killerCheck.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
	with open(logFile,'a') as f:
		f.write(logMsg)

def mailBad(msg):
    mail('burnnxx1@gmail.com','DAS5 - '+msg,msg+ ' '+str(datetime.datetime.now()))
    
def remain(h,m):
    stopTime = (dt.now()).replace(hour=h, minute=m, second=0, microsecond=0)
    return int((stopTime - dt.now()).total_seconds())
        
def killer(h,m):
    msg = 'DAS5 - Killer called with endTime - '+str(h)+':'+str(m)
    log(msg)
    print(msg)
    log('DAS5 - Entering timer failover')
    stopTime = (dt.now()).replace(hour=h, minute=m, second=0, microsecond=0)
    delay = int((stopTime - dt.now()).total_seconds())
    msg = 'DAS5 - Killer. Delay estimated - '+str(delay)
    log(msg)
    print(msg)
    log('DAS5 - Entering timer failover')
    time.sleep(delay)
    timeUp = 0
    print('DAS5 - Entering timer failover')
    log('DAS5 - Entering timer failover')
    while timeUp == 0:        
        if dt.now() > stopTime:
            timeUp = 1
            msg = "DAS5 - Time Up"
            print(msg)
            log(msg)
        else:
            msg = "DAS5 - Still running. Sleeping for 30 seconds"
            print(msg)
            time.sleep(30)
            log(msg)