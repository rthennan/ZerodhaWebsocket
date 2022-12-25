1. Download NSE holidays and save it as tradeHolidays.xlsx
2. Ensure the date column is titled 'Date'. It is expected to be in the format '%B %d, %Y' . Example - 'January 26, 2023'
3. Upload it to the expiryGenerator directory.
4. Run expSuffGenerator.py. This will produce   - A single list with the Dates in yyyy-mm-dd format.  
Use tradingHolidays_ref.csv for reference.  
tradingHolidays.csv and a copy of tradeHoliday.xlsx suffixed with the year are then pushed to ../../tradeHoliday.  
Comment the approrpriate lines of code if you don't want this file operation to be performed.
