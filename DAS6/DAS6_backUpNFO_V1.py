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

def backUpNFOFULL():
    def log(txt):
    	directory = path.join('Logs',str(datetime.date.today())+'_DAS6Logs')
    	if not path.exists(directory):
    		makedirs(directory)
    	logFile = path.join(directory,str(datetime.date.today())+'_backUpNFOFULL.log')
    	logMsg = '\n'+str(datetime.datetime.now())+'    ' + txt
    	with open(logFile,'a') as f:
    		f.write(logMsg)
    try:
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()
        c.execute("SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = 'aws_das3full'")
        if c != 0:
            tables = list([item[0] for item in c.fetchall()])    
        failedTables = 0
        #Checking and creating tables in das2 just in case
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das3fulldump")
        for table in tables:
            try:
                c.execute("CREATE TABLE IF NOT EXISTS aws_das3fulldump.`"+table+"` LIKE aws_das3full.`"+table+"`")
                c.execute("REPLACE INTO aws_das3fulldump.`"+table+"` SELECT * FROM aws_das3full.`"+table+"`") 
                msg = "Table "+str(table) + " Backedup successfully. Dropping it now"
                log(msg)
                c.execute("DROP TABLE aws_das3full.`"+table+"`")
            except Exception as e:
                msg = "DAS6 - couldn't Backup table "+str(table)+" . Reason : "+str(e)
                log(msg)
                failedTables = failedTables +1

        if failedTables > 0:
            mail("burnnxx1@gmail.com","DAS6 - backUpNFOFULL failed", "backUpBNFOFULL failed for " + str(failedTables)+" Tables. Check "+ str(datetime.date.today())+"_backupNFO.log for details")
        c.close()
        conn.close()
        msg = "DAS6 - NFO Backup and Truncate successfull"
        log(msg)
        return True
    except Exception as e:
        msg = "DAS6 - backUpNFOFULL - Backup and Truncate Couldn't be completed. Reason: "+str(e)
        log(msg)
        mail("burnnxx1@gmail.com","DAS6 - backUpBNFOFULL Failed",msg)
        return False
        