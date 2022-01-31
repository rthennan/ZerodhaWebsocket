import datetime
import threading
import sys
import os
import smtplib
import json


credsFile = os.path.join('..','creds.json')
with open(credsFile,'r') as credsFile:
    creds = json.load(credsFile)

senderEmailAddress = creds['senderEmailAddress']
senderEmailPass = creds['senderEmailPass']

# =============================================================================
# The main code actually call mailer for notification will have to wait for the mail to be sent.
# Hence instead of starting a new thread for mail in every code (I have used a lot of notifications), I have set the primary mailer to start
# as a separate thread
# =============================================================================

def log(txt):
	directory = os.path.join('mailLogs',str(datetime.date.today())+'_Logs')
	if not os.path.exists(directory):
		os.makedirs(directory)
	logFile = directory+'/'+str(datetime.date.today())+'_mailer.log'
	logMsg = '\n'+str(datetime.datetime.now())+'    ' + str(txt)
	with open(logFile,'a') as f:
		f.write(logMsg)
        
def mailer(recipient, subject, body):
    try:
        subject = 'AWS : '+subject
        thredMail = threading.Thread(target=mailerActual,args=(recipient,subject,body,))
        thredMail.start()
    except Exception as e:
        msg = 'send mail failed : '+str(e)
        lineNoMailException =sys.exc_info()[-1].tb_lineno
        print(msg)
        print(lineNoMailException)
        log(msg)
        log(lineNoMailException)

def mailerActual(recipient, subject, body):
    pwd = senderEmailPass
    FROM = senderEmailAddress
    user = FROM
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject + " " + str(datetime.date.today())
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        msg = "Mail with subject '" + SUBJECT + "' sent Succesfully to "+ recipient
        print(msg)
        log(msg)
    except Exception as e:
        msg = 'Exception : '+str(e)
        lineNoMailException =sys.exc_info()[-1].tb_lineno
        print(lineNoMailException)
        print(msg)
        log(lineNoMailException)
        log(msg)