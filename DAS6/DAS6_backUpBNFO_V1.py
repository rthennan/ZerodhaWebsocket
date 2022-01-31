import datetime
import MySQLdb
from sendMailV1 import mailer as mail
from os import path,makedirs
import json
credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)
mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
destinationEmailAddress = creds['destinationEmailAddress']

def backUpBNFOFULL():
    def log(txt):
    	import datetime
    	directory = path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
    	if not path.exists(directory):
    		makedirs(directory)
    	logFile = path.join(directory,str(datetime.date.today())+'_backUpBNFOFULL.log')
    	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
    	with open(logFile,'a') as f:
    		f.write(logMsg)
    try:
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()
        c.execute("SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = 'aws_das2optionsdaily'")
        if c != 0:
            tables = list([item[0] for item in c.fetchall()])    
        failedTables = 0
        #Checking and creating tables in das2 just in case
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das2options")
        for table in tables:
            try:
                c.execute("CREATE TABLE IF NOT EXISTS aws_das2options.`"+table+"` LIKE aws_das2optionsdaily.`"+table+"`")
                c.execute("REPLACE INTO aws_das2options.`"+table+"` SELECT * FROM aws_das2optionsdaily.`"+table+"`") 
                msg = "Table "+str(table) + " Backedup successfully. Dropping it now"
                log(msg)
                c.execute("DROP TABLE aws_das2optionsdaily.`"+table+"`")
            except Exception as e:
                msg = "DAS6 - couldn't Backup table "+str(table)+" . Reason : "+str(e)
                log(msg)
                failedTables = failedTables +1

        if failedTables > 0:
            mail(destinationEmailAddress,"DAS6 - backUpBNFOFULL failed", "backUpBNFOFULL failed for " + str(failedTables)+" Tables. Check "+ str(datetime.date.today())+"_backupNFO.log for details")
        c.close()
        conn.close()
        msg = "DAS6 - BNFO Backup and Truncate successfull"
        log(msg)
        return True
    except Exception as e:
        msg = "DAS6 - backUpBNFOFULL - Backup and Truncate Couldn't be completed. Reason: "+str(e)
        log(msg)
        mail(destinationEmailAddress,"DAS6 - backUpBNFOFULL Failed",msg)
        return False
        