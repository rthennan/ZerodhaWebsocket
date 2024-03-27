"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan
"""

from datetime import datetime as dt
import sys
from os import path

#Expects DAS_gmailer and tradeHolidayCheck to be in the same path 
# Get the absolute path of the current file
scriptAbsolutePath = path.abspath(__file__)
#Get Directory
# Get the directory of the current script
scriptDirectory = path.dirname(scriptAbsolutePath)

# Append the script directory to the system path
if scriptDirectory not in sys.path:
    sys.path.append(scriptDirectory)
# Allows importing DAS_gmailer  irrespective of where traceHolCheck is called from 
from DAS_gmailer import DAS_mailer
    
DAS_mailer('DAS - Machine started Successfully',f'DAS - Machine started Successfully Successfully at {str(dt.now().replace(microsecond=0))}')
