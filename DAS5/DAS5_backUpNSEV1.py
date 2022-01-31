# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 19:15:16 2019

@author: Thennan
"""

import datetime
import MySQLdb
from sendMailV1 import mailer as mail
from mailAttachment import sendMailAttach 
from os import path, makedirs
import pandas as pd
import json

credsFile = path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

mysqlHost = creds['mysqlHost']
mysqlUser = creds['mysqlUser']
mysqlPass = creds['mysqlPass']
destinationEmailAddress = creds['destinationEmailAddress']

    
def log(txt):       
    directory = path.join('Logs',str(datetime.date.today())+'_DAS5Logs')
    if not path.exists(directory):
        makedirs(directory)
    logFile = path.join(directory,str(datetime.date.today())+'_backUpNSE.log')
    logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
        f.write(logMsg)        
        
def backUpNSE():
    print('Backup NSE Started')
    try:
        conn = MySQLdb.connect(host = mysqlHost, user = mysqlUser, passwd = mysqlPass)
        conn.autocommit(True)
        c = conn.cursor()
        c.execute("SELECT TABLE_NAME FROM `information_schema`.`tables` WHERE `table_schema` = 'aws_das4daily'")
        tables = list([item[0] for item in c.fetchall()])
        c.execute("CREATE DATABASE IF NOT EXISTS aws_das4")
        blankTables=[]
        failedTables = 0
        for table in tables:
            c.execute("CREATE TABLE IF NOT EXISTS aws_das4."+table+" LIKE aws_das4daily."+table)
            try:
                c.execute("REPLACE aws_das4.`"+table+"` SELECT * FROM aws_das4daily.`"+table+"`")  
                msg = "Table "+str(table) + " Backedup successfully. Truncating it now"
                log(msg)                
                c.execute("SELECT COUNT(*) FROM aws_das4daily.`"+table+"`")
                tbRowCount=c.fetchone()[0]
                if tbRowCount<=10:
                    #Check if there are tables with lesser rows
                    blankTables.append({'tbName':table,'rowCount':tbRowCount})
                c.execute("DROP TABLE aws_das4daily.`"+table+"`")
            except Exception as e:
                msg = "DAS5 - couldn't Backup table "+str(table)+" . Reason : "+str(e)
                log(msg)
                failedTables = failedTables +1           

        if failedTables > 0:
			#Notify on tables with lesser rows
            mail(destinationEmailAddress,"DAS5 - backUpNSE failed", "backUpNSE failed for " + str(failedTables)+" Tables. Check "+ str(datetime.date.today())+"_backUpNSE.log for details")
        if len(blankTables)>0:
            blankTablesDF = pd.DataFrame(blankTables, columns =['tbName', 'rowCount']) 
            todayTabs=str(datetime.date.today())+"smallTables.xlsx"
            blankTablesDF.to_excel(path.join('smallTables',todayTabs),index=False)
            sendMailAttach(destinationEmailAddress,"DAS5 - "+str(len(blankTables))+" small Tables found during DAS5 - NSE Backup ","DAS5 - "+str(len(blankTables))+" small Tables found during DAS5 - NSE Backup "+'\n\n',path.join('smallTables',todayTabs))
            log(str(len(blankTables))+" small Tables found. Check "+ str(datetime.date.today())+"smallTables.xlsx for details")
        else:
            log("No small Tables found.")
            mail(destinationEmailAddress,"No small Tables found in DAS5 - NSE Backup ","No small Tables found in DAS5 - NSE Backup")
			
        c.close()
        conn.close()
        msg = "DAS5 - Backup and Truncate successfull"
        log(msg)        
        return True
    except Exception as e:
        msg = "DAS5 - Backup and Truncate Couldn't be completed. Reason: "+str(e)
        log(msg)
        mail(destinationEmailAddress,"DAS5 - NSE Backup Failed",msg)
        try:
            c.close()
            conn.close()
        except:
            pass          
        return False