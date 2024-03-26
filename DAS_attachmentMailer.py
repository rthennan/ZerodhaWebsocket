import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime as dt, date
from os import path, makedirs
import sys
import json
import traceback
from DAS_errorLogger import DAS_errorLogger


def attachMailLogger(txt):
    print(dt.now(),txt)
    logDirectory = path.join('Logs',str(date.today())+'_DAS_Logs')
    if not path.exists(logDirectory):
        	makedirs(logDirectory)
    logFile = path.join(logDirectory,f'DAS_attachmentMailer_logs_{str(date.today())}.log')
    logMsg = '\n'+str(dt.now())+'    ' + str(txt)
    with open(logFile,'a') as f:
    	f.write(logMsg)

#mailer(recipient, subject, body)
def sendMailAttach(subject, message, attachFile):
    configFile = 'dasConfig.json'
    with open(configFile,'r') as configFile:
        dasConfig = json.load(configFile)
    recipientEmailAddress = dasConfig['destinationEmailAddress']
    #Generate a list if multiple recipients mentioned
    recipientEmailAddress = recipientEmailAddress.split(',')
    senderEmailAddress = dasConfig['senderEmailAddress']
    senderEmailPass = dasConfig['senderEmailPass']
    #Gmail App password - https://support.google.com/mail/answer/185833?hl=en
    try:
        if isinstance(recipientEmailAddress, list):
            recipientEmailAddressStr = ', '.join(recipientEmailAddress)
        else:
            recipientEmailAddressStr = recipientEmailAddress
        msg = MIMEMultipart()
        pwd=senderEmailPass
        send_from =senderEmailAddress    
        user= senderEmailAddress
        msg['From'] = senderEmailAddress
        msg['To'] = recipientEmailAddressStr
        msg.attach(MIMEText(message))
        msg['Subject'] = subject + " " + str(date.today())
        part = MIMEBase('application', "octet-stream")
        with open(attachFile, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition','attachment; filename="{}"'.format(path.basename(attachFile)))
        msg.attach(part)       
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(send_from, recipientEmailAddress, msg.as_string())
        server.quit()
        if '/' in attachFile:
            fNameStart=(attachFile.rfind('/'))+1
            fName = attachFile[fNameStart:]
        else:
            fName = attachFile
        msg = f'Mail with subject {subject} and Attachment {fName} sent Succesfully to {recipientEmailAddress}'

    except Exception as e:
        lineNo =sys.exc_info()[-1].tb_lineno
        logMsg = f'Exception : {e} in Line No. {lineNo}. Traceback : {traceback.format_exc()}'
        attachMailLogger(logMsg)
        DAS_errorLogger('DAS_attachmentMailer - '+logMsg)