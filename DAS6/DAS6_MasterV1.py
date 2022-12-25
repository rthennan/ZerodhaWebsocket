import sys
import os
import multiprocessing
import datetime
from DAS6_NFOmainV1 import NFO #Moded for Linux
from DAS6_BNFOmainV1 import BNFO #Moded for Linux
from DASfailMsg import DASfail as fail #Moded for Linux
from sendMailV1 import mailer as mail #Moded for Linux
from DAS6_backUpBNFO_V1 import backUpBNFOFULL #Moded for Linux
from DAS6_backUpNFO_V1 import backUpNFOFULL #Moded for Linux
from lookupTab import lookup
import json


credsFile = os.path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

senderEmailAddress = creds['senderEmailAddress']
senderEmailPass = creds['senderEmailPass']
destinationEmailAddress = creds['destinationEmailAddress']


marketCloseHH = 15
marketCloseMM = 35




def log(txt):
	directory = os.path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = os.path.join(directory,'_DAS6Master.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg)
#Starting Isntrument Token Loookup
if __name__ == '__main__': 
    lookup()
    nfo = multiprocessing.Process(target=NFO, args=(marketCloseHH,marketCloseMM,))
    bnfo = multiprocessing.Process(target=BNFO, args=(marketCloseHH,marketCloseMM,))
    
    dataDumpJobs = []
    dataDumpJobs.append(nfo)
    dataDumpJobs.append(bnfo)
    nfo.start()
    bnfo.start()
    for job in dataDumpJobs:
        job.join()
    #killer(marketCloseHH,marketCloseMM)
    
    backUpNFOStat = backUpNFOFULL()
    backUpBNFOStat = backUpBNFOFULL()
    
    if backUpBNFOStat and backUpNFOStat:
        msg="All Backups Successfull. DAS6 Activities for the day have been completed"
        log(msg)
        mail(destinationEmailAddress,"DAS6 Done for the day",msg)
    else:
        msg = "DAS6 - One or More Activities failed. Check logs thoroughly"
        log(msg)
        fail(msg)
        sys.exit()
