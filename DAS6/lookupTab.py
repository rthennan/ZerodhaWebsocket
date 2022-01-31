import datetime
import urllib.request
from sendMailV1 import mailer as mail
import MySQLdb
import json
from os import path, makedirs

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)
mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
destinationEmailAddress = creds['destinationEmailAddress']

def lookup():
    
    def log(txt):
    	directory = path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
    	if not path.exists(directory):
    		makedirs(directory)
    	logFile = path.join(directory,'_Lookup.log')
    	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
    	with open(logFile,'a') as f:
    		f.write(logMsg)              

    try:    
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()   
        
        #Removing Empty BNFO Tables
        c.execute("SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = 'aws_das2optionsdaily' and TABLE_ROWS=0")
        if c != 0:
            emptyTables = list([item[0] for item in c.fetchall()])
            for emptyTable in emptyTables:
                c.execute("DROP TABLE aws_das2optionsdaily.`"+emptyTable+"`")        
                
        #Removing Empty NFO Tables
        c.execute("SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = 'aws_das3full' and TABLE_ROWS=0")
        if c != 0:
            emptyTables = list([item[0] for item in c.fetchall()])
            for emptyTable in emptyTables:
                c.execute("DROP TABLE aws_das3full.`"+emptyTable+"`")                    
        c.close()
        conn.close()

    except Exception as e:
        log(str(e))
        print("DAS6 Couldn't drop empty tables "+str(e))
        log("Couldn't drop empty tables. Exception =>"+str(e))        
        
    try:          
        #Downloading the instrument list
        lookupDirectory = 'lookup_tables'
        if not path.exists(lookupDirectory):
            makedirs(lookupDirectory)
        tslice = str(datetime.date.today())
        fname = path.join('lookup_tables','instruments_'+tslice+'.csv')
        urllib.request.urlretrieve ('https://api.kite.trade/instruments', fname)        
        msg = 'DAS6 Started.Access and Token lookup Successful'
        log(msg)
        print(msg)
        mail(destinationEmailAddress,msg,'DAS6: Instrument Lookup succeeded at '+str(datetime.datetime.now())+'\n Proceeding to Dumps')
        return True

    except Exception as e:
        log(str(e))
        print("Instrument Token Lookup Failed "+str(e))
        mail(destinationEmailAddress, 'DAS6: Instrument Token Lookup Failed',str(e))
        return False
    
