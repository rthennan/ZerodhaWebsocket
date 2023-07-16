## **Sequence to run DAS5 scripts**:
1. accessTokenReq.py
2. accessTokenReqDAS6.py
3. DAS5_MasterV1.py

## **AccessToken: - accessTokenReq and accessTokenReqDAS6**  
Uses the provided credentials, generates an access token for Zerodha API and stores it in the aws_tokens.das5 and das6 tables.  
I have used a Selenium driver for Chrome to automate this task. The first half of what the gentleman does [here](https://www.youtube.com/watch?v=TaJnJPBdQzU) manually.  
The access token, along with the API Key and secret, will be required to establish the WebSocket connection later.  
accessTokenReq and accessTokenReqDAS6 do the same job but for different apps (API key, secret and access token).  
I had split them into two cause I felt Selenium might misbehave if I tried to open two windows from the same code. Not to mention the need to time it properly.  
It is to be noted that I am using Selenium in headless mode here.  
accessTokenReq and accessTokenReqDAS6 are independent and can be run at the same time.  
  
I have uploaded a [YouTube video](https://www.youtube.com/watch?v=0A-bnJRNJQk) demoing the accessToken automation in Windows.  

### **Symbol Name to Table mapping**
- Index Futures also have a naming convention. BANKNIFTY22JANFUT, for example, is the BankNifty Futures instrument for January 2022.
- I am interested only in the current month's future.
- lookupIns will check if yesterday was the last Thursday of the month. (today is the beginning of a new monthly expiry cycle).  
  If yes, it generates the instrument symbol for the current month and updates instrumentsLookup.xlsx.
- This way, the current month's index future tick data is always stored in the 'BANKNIFTYFUT' table, irrespective of the actual symbol (example: BANKNIFTY22JANFUT)
- The same is done for Nifty as well.
- The symbol for a few stocks has special characters in them. Example - M&M.
- So, a corresponding table without special characters in its name (M_M) is created).
  I use the lookup tables to handle this mapping as well. More on this later.  

## **DAS5_MasterV1.py**
  1. Import and run lookupIns
  2. Import custom ticker modules - DAS5_tickerV1, DAS5_2_tickerV1, DAS5_3_tickerV1 and DAS5_4_tickerV1
  3. Also import backUpNSE(DAS5_backUpNSEV1) and backUpIndex(DAS5_backUpIndexV1)
  4. If lookupIns is successful:
     - Start The tickers (DAS5_tickerV1, etc) as individual processes.
     - Wait for killer to finish. killerCheck.py - Just sleeps till market close time (15:35 IST)
  5. After Killer is done, kill the processes started earlier
  6. Run backUpNSE and backUpIndex

## **Explanation for DAS5_Master's individual steps:**  
### **lookupIns.py**
- Downloads the latest list of instrument_token along with ticker symbols from https://api.kite.trade/instruments and stores it in the lookup_tables folder.
- Updates Nifty and BankNifty Futures instrument names if applicable (last Thursday's stuff mentioned above).
- Checks the instrument list I have manually provided in the below files in the lookup_tables folder:
  - instrumentsLookup.xlsx (Nifty 50, Nifty and BankNifty Index and their current month futures)
  - instrumentsLookup_DAS5_2.xlsx
  - instrumentsLookup_DAS5_3.xlsx
  - instrumentsLookup_DAS5_4.xlsx
    instrumentsLookup_DAS5_2, instrumentsLookup_DAS5_3 and instrumentsLookup_DAS5_4 are just the remainder of Nifty500 stocks (-Nifty50).
- Retains data only for these symbols in the instrument_token list.
- Generates nseTokenList and nseTokenTable variants and stores them in the lookup_tables folder.
- nseTokenList, nseTokenList2, nseTokenList3 and nseTokenList4 are generated:
    - Going back to the M&M example, in order to subscribe to M&M, we need to provide its instrument_token. 
      So lookupIns uses M&M as a reference to get its instrument_token from the downloaded list. 
    - If M&M's instrument_tokentoday is 519937, it is added to nseTokenList. 
    - This instrument_token is stored in a list of tokens.
    - Each of the nseTokenList variants holds a set of tokens and is accessed by different ticker scripts (more on this later)
- nseTokenTable.npy, nseTokenTable2.npy, nseTokenTable3.npy and nseTokenTable4.npy:
    - The ticket data received from Zerodha includes the corresponding instrument_token, amongst [other things](https://kite.trade/docs/connect/v3/websocket/#modes).  
    - Once we start receiving the data stream, it is critical to segregate the tick data and store it in the correct table.
    - I have utilized the instrument_token for this.
    - lookupIns creates a dictionary, with the instrument_tokens as the keys and the corresponding table names as the values.
    - These dictionaries make up the nseTokenTable.py variants.
    - For the M&M example, 519937 would be the key and 'M_M' would be the value. So the value for the instrument_token's key would tell the ticker which table the data should be stored in.
- Creates tables for all the instruments provided in the instrumentsLookup files.

### **Ticker Modules - DAS5_tickerV1:**  
- Fetch the latest access token from the aws tokens table.
- Connect to Zerodha's WebSocket.
- Subscribe to the corresponding instrument_tokens.
- Store the received data in the corresponding tables.
  - DAS5_tickerV1 subscribes to stocks and indices.
  - Stock data has 40+ columns, but index data has only two columns.
  - So, I have added steps to use different SQL statements for stock and Index data.
 - **Uses apiKey1 and apisec1**  

### **DAS5_2_tickerV1, DAS5_3_tickerV1 and DAS5_4_tickerV1:**  
- Same as DAS5_tickerV1, but without the index tables part and for NIFTY500 (Excluding NIFTY50).
- **All three use apiKey2 and apisec2**

### **backUpNSE and backUpIndex:**
- Fetches data from the 'Daily' tables.
- Removes data before 09:15 and after 15:30.
- Reports if any of the tables were empty. Empty tables are indications of tech / logical issues. They could also be caused by changes in Stock Symbols.
- Stores the valid data in the main database.
- Delete the 'Daily' tables
- DAS5_tickerV1

### **Weekly or monthly activity - DAS5/nifty500Updater.py**  
It is important to look out for additions to Nifty500 as they might eventually be added to Nifty50 or BankNifty indexes.  
Fully automating this is not optimal, as it will not work for symbol changes.  
1. Check small tables and update/remove symbol names in instrumentsLookup.xlsx, instrumentsLookup_DAS5_2.xlsx, instrumentsLookup_DAS5_3.xlsx and instrumentsLookup_DAS5_4.xlsx
    Update - Update the new symbol on symbol change. Retain the same Table name  
    Remove - remove the entire row on delisting  
2. Then run DAS5/nifty500Updater.py to identify missing symbols
   These would be new instruments added to the Nifty500 list
   Add the new symbols to instrumentsLookup_DAS5_4.xlsx
