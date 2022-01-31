import sys
import multiprocessing
import datetime
from lookupIns import lookup #Moded for Linux
from DASfailMsg import DASfail as fail  #Moded for Linux
from sendMailV1 import mailer as mail #Moded for Linux
from killerCheck import killer #Moded for Linux
from DAS5_tickerV1 import DAS5_Ticker as DAS_Ticker #Moded for Linux
from DAS5_2_tickerV1 import DAS5_2_Ticker as DAS5_2_Ticker #Moded for Linux
from DAS5_3_tickerV1 import DAS5_3_Ticker as DAS5_3_Ticker #Moded for Linux
from DAS5_4_tickerV1 import DAS5_4_Ticker as DAS5_4_Ticker #Moded for Linux
from DAS5_backUpNSEV1 import backUpNSE #Moded for Linux
from DAS5_backUpIndexV1 import backUpIndex #Moded for Linux
import json
from os import path, makedirs

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

destinationEmailAddress = creds['destinationEmailAddress']

marketCloseHH = 15
marketCloseMM = 35

def log(txt):
	directory = path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
	if not path.exists(directory):
		makedirs(directory)
	logFile = path.join(directory,str(datetime.date.today())+'_DAS5Master.log')
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
	with open(logFile,'a') as f:
		f.write(logMsg)
#Starting Isntrument Token Loookup
if __name__ == '__main__':
    if lookup():
        ticks = multiprocessing.Process(target=DAS_Ticker)
        ticks2 = multiprocessing.Process(target=DAS5_2_Ticker)       
        ticks3 = multiprocessing.Process(target=DAS5_3_Ticker) 
        ticks4 = multiprocessing.Process(target=DAS5_4_Ticker) 
        ticks.start()
        ticks2.start()
        ticks3.start()
        ticks4.start()
        killer(marketCloseHH,marketCloseMM)

### Killing Dumps ###        
        try:
            ticks.terminate()
            ticks2.terminate()
            ticks3.terminate()
            ticks4.terminate()
            ticksClose =True
        except Exception as e:
            msg = "DAS5 Exception: NSE Dump couldn't be stopped "+str(e)
            fail(msg)
            print(msg)
            log(msg)

        if ticksClose:
            backUpNSEstatus = backUpNSE()
            backUpIndexStatus = backUpIndex()
        else:
            backUpIndexStatus = backUpNSEstatus = False
          
        
        if backUpNSEstatus and backUpIndexStatus:
            msg="All Backups Successfull. DAS5 Activities for the day have been completed"
            log(msg)
            mail(destinationEmailAddress,"DAS5 Done for the day",msg)
        else:
            msg = "DAS5 - One or More Activities failed. Check logs thoroughly"
            log(msg)
            fail(msg)
            sys.exit()
    else:
        msg = "DAS5 - One or More Activities failed. Check logs thoroughly"
        log(msg)
        fail(msg)
        sys.exit()