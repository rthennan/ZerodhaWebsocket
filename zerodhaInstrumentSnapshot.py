"""
Author: Rajesh Thennan
Source: https://github.com/rthennan/ZerodhaWebsocket

Download Zerodha Instrument list and save it with today's date
"""

from os import path, makedirs
import urllib.request
from datetime import date

try:
    storeDirectory = 'zerodhaInstrumentDumps'
    if not path.exists(storeDirectory):
        makedirs(storeDirectory)
    tslice = str(date.today())
    fname = path.join(storeDirectory,'zerodhaInstruments_'+tslice+'.csv')
    urllib.request.urlretrieve('https://api.kite.trade/instruments', fname)
    print(f'Zerodha Intrument dump for the day saved as {fname}')
except Exception as e:
    print(f'Excaption while downloading/saveing Zerodha Instrument dump: {e}')

