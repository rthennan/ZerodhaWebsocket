"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket
LinkedIn: https://www.linkedin.com/in/rthennan
"""
from DAS_gmailer import DAS_mailer
from datetime import datetime as dt
    
DAS_mailer('DAS - Machine started Successfully',f'DAS - Machine started Successfully Successfully at {str(dt.now().replace(microsecond=0))}')
