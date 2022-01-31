import smtplib
import os.path as op
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import datetime
import os
import sys
import json


credsFile = os.path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)
senderEmailAddress = creds['senderEmailAddress']
senderEmailPass = creds['senderEmailPass']
destinationEmailAddress = creds['destinationEmailAddress']

def log(txt):
	import datetime
	directory = 'Logs/'+str(datetime.date.today())+'_DAS5Logs'
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = directory+'/'+str(datetime.date.today())+'_attachmetMailer.log'
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
	with open(logFile,'a') as f:
		f.write(logMsg)

#mailer(recipient, subject, body)
def sendMailAttach(recipient, subject, message, attachFile):
    try:
        msg = MIMEMultipart()
        pwd=senderEmailPass
        send_from =senderEmailAddress    
        user= senderEmailAddress
        msg['From'] = senderEmailAddress
        msg['To'] = recipient
        msg.attach(MIMEText(message))
        msg['Subject'] = subject + " " + str(datetime.date.today())
        part = MIMEBase('application', "octet-stream")
        with open(attachFile, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition','attachment; filename="{}"'.format(op.basename(attachFile)))
        msg.attach(part)       
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(send_from, recipient, msg.as_string())
        server.quit()
        if '/' in attachFile:
            fNameStart=(attachFile.rfind('/'))+1
            fName = attachFile[fNameStart:]
        else:
            fName = attachFile
        logMsg = 'Mail with subject '+ subject +' and Attachment '+fName+' sent Succesfully to '+ recipient
        print(logMsg)
        log(logMsg)

    except Exception as e:
        lineNo =sys.exc_info()[-1].tb_lineno
        logMsg = 'Exception : '+'Line No. '+str(lineNo)+'\t'+str(e)
        print(logMsg)
        log(logMsg)