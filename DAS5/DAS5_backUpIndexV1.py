import datetime
import MySQLdb
import json
from os import path, makedirs
from sendMailV1 import mailer as mail

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
destinationEmailAddress = creds['destinationEmailAddress']

def backUpIndex():
    tables =  ['BANKNIFTY','NIFTY']
    
 
    def log(txt):
        directory = path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
        if not path.exists(directory):
            makedirs(directory)
        logFile = path.join(directory,str(datetime.date.today())+'_backupIND.log')
        logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
        with open(logFile,'a') as f:
            f.write(logMsg)            
            
    try:
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()
        
        #Checking and creating tables in das2 just in case
        c.execute("create table if not exists aws_das2.BANKNIFTY like aws_das2daily.BANKNIFTY")
        c.execute("create table if not exists aws_das2.NIFTY like aws_das2daily.NIFTY") 
        msg = "Checking If Index Tables exist - Done"
        log(msg)
        #Dumping from das2optionsdaily to das2options
        for table in tables:
            #das temp table count
            failedTables = 0
            try:
                c.execute("REPLACE aws_das2.`"+table+"` SELECT * FROM aws_das2daily.`"+table+"`")
                msg = "Executed - REPLACE aws_das2.`"+table+"` SELECT * FROM aws_das2daily.`"+table+"`"
                log(msg)
                c.execute("DROP TABLE aws_das2daily.`"+table+"`")
                msg = "DROP TABLE aws_das2daily.`"+table+"`"
                log(msg)
            except Exception as e:
                msg = "DAS5 - couldn't Backup table "+str(table)+" . Reason : "+str(e)
                log(msg)
                failedTables = failedTables +1
        if failedTables > 0:
            mail(destinationEmailAddress,"DAS5 - Index Back up failed", "Index Backup failed for " + str(failedTables)+" Tables. Check "+ str(datetime.date.today())+"_backupIND.log for details")
        c.close()
        conn.close()
        msg = "DAS5 - Index Backup and Truncate successfull"
        log(msg)
        return True

    except Exception as e:
        msg = "DAS5 - Index Backup and Truncate Couldn't be completed. Reason: "+str(e)
        log(msg)
        mail(destinationEmailAddress,"DAS5 - Index Backup Failed",msg)
        return False
        