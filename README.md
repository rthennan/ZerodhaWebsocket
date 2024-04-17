# Zerodha Websocket for Nifty500, Nifty Options and BankNifty Options
Acquire and store tick data for NSE (India) stocks, Index Futures and Index Options from Zerodha.  

Highlights:
 - Automates entire pipeline including daily login for Zerodha API app.
 - Dynamically gets the latest Nifty 500 list and weekly options for current and next week for Nifty and Bank Nifty
 - The Nifty 500 list is maintained and **appended** locally.  
   - When the Nifty 500 list is updated by NSE, only additions are updated in the local list. If a stock is removed from Nifty 500, the code still retains it and tries subscribing to it.
   - This also allows you to add additional instruments that may or may not be part of the Nifty 500 to the lookup list.
- Checks for trading holidays every day and shuts down if it is an NSE trading holiday.
- The only maintenance required is to ensure there is adequate storage available for the database.

**DAS** - Data Acquisition System. That is what I am calling it.


## **Contents:**  
### **[1. Pre-requisites](#pre-requisites)**
### **[2. Tools/Packages primarily used](#toolspackages-primarily-used)**
### **[3. OS Supported](#os-supported)**
### **[4. Setup/Installation](#setupinstallation-)**
   - **4.1 Install Python3**
   - **4.2 Install MySQL/MariaDB Server**
   - **4.3 MySQL/MariaDB Client**
   - **4.4 Install Google Chrome**
   - **4.5 Install the MySQL/MariaDB client packages at the OS level. Else, pip install will fail for mysqlclient**
   - **4.6 Download / Clone this repo**
   - **4.7 [Update dasConfig.json](#2-update-dasconfigjson)**
   - **4.8 Customize lookupTables > lookupTables_Nifty500.csv with additional instruments**
   - **4.9 pip install -r requirements.txt** 
### **[5. To Execute](#to-execute)**
### **[6. Detailed explanation of the Functions](#but-what-does-it-do)**
### **[7. Functions outside the scope of DAS](#scripts-outside-the-scope-of-das_main-that-i-use-and-are-completely-optional)**
   - **sysStartupNotify.py** - Email when the machine starts up. Cronjob @reboot
   - **tradeHolCheck_shutDown.py** - Shut the machine down if today is a trading Holiday
   - **getExpiryPrefix** - Generate the prefix for Nifty and BankNifty Option instruments. Useful in backtests.
### **[8. Automation I use outside the provided code](#automation-i-use-outside-the-provided-code)**
### **[9. Changelog](#changelog)**
   - **[2024-03-27](#2024-03-27)**
   - **[2024-04-11](#2024-04-11)**   
### **[11. Performance Tweaks](##performance-tweaks)** 
### **[10. Raise Issues](##raise-issues)**     



 ### **Pre-requisites:**
- Active subscription for one [Kite Connect API](https://developers.kite.trade/apps) app.
- Python3
- MySQL/MariaDB Server
- Gmail account with App password configured - [Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en)
- Zerodha, Gmail and MySQL credentials have to be filled in the dasConfig.json file
  - Storing passwords and keys in a plaintext file poses a potential security risk.
  - This is used for simplicity. Please consider switching to more secure secret management options (like environment variables) for production deployments.
  - All calls for reading dasConfig.json and using the json would have to be updated.  
 
### **Tools/Packages primarily used:**
- Pandas - For storing ticks and handling CSV Files
- Selenium - Automate Kite Authentication and getHolidayList from NSE
- MySQL/MariaDB for persistent store of ticker data
- numpy - Mainly used to save token lists and dictionaries for ticker subscriptions and stores. Pickle could have been used
- smtplib - Mail notification using Gmail
- pyotp - for generating TOTP required for Zerodha authentication
- json - for storing and accessing credentials, API keys, etc. (dasConfig.json)

### OS Supported:
- Tested in Windows (10 and 11) and Linux (Ubuntu)
- Should work in other Linux Distros as well. The steps for installing MySQL Client and Google Chrome will be different
- I don't see why it wouldn't work on MacOS. But NOT tested.

### Setup/Installation :
- Install Python3
- Install MySQL/MariaDB Server
- MySQL Client
    -   For Windows: https://stackoverflow.com/questions/34836570/how-do-i-install-and-use-mysqldb-for-python-3-on-windows-10
    -   For Linux  
        `sudo apt-get update`  
        `sudo apt-get install libmysqlclient-dev` 
         or
        `sudo apt-get install libmariadb-dev`
        
-   Install Google Chrome
    - For Linux
        - `wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`
        - `sudo dpkg -i google-chrome-stable_current_amd64.deb`
- Ensure you have installed the MySQL client packages at the OS level. Else, pip install will fail for mysqlclient

#### 1. Download / Clone this repo:
  - `git clone https://github.com/rthennan/ZerodhaWebsocket.git`
#### 2. Update dasConfig.json:
Ensure all fields with **Invalid default** values are updated.  
Update the rest as required.  
- `destinationEmailAddress` :
  -   Startup, Completion and Failure notifications will be sent to the address(es) mentioned here.
  -   One email address or multiple separated by commas.
  -   Default value  **Invalid**  
- `senderEmailAddress` :
  -   Used to send the notifications. 
  -   Gmail account with App password configured - [Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en)
  -   If you use a non-Gmail address, update SMTP details in DAS_gmailer.py and DAS_attachmentMailer.py
  -   Default value - `Your_SenderEmailAddressATgmail.com` - **Invalid**
- `senderEmailPass` :
  -   App password for senderEmailAddress - [Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en)
  -   Default value - **Invalid**
- `TOTP_seed` :
  -   TOTP_seed used for generating Zerodha TOTP. **NOT THE 6-digit TOTP itself.** The actual seed used to generate the TOTP.
  -   You might have to reset your TOTP to get the seed if you don't have it saved - [Zerodha - What to do if the access to the Time-based OTP (TOTP) Authenticator app is lost?](https://support.zerodha.com/category/your-zerodha-account/login-credentials/login-credentials-of-trading-platforms/articles/lost-totp-app)
  -   Default value - `Your_TOTP_seed` - **Invalid**
- `ZerodhaLoginName`, `ZerodhaPass`, `apiKey` and `apisec` :
  -   Client and Client API credentials from Zerodha.
  -   Default values - **Invalid**
- `mysqlHost`, `mysqlUser`, `mysqlPass` :
  -   MySQL/MariaDB  connection details.
  -   Default values - **Invalid**
- `mysqlPort` :
  -   Update this if your DB Server runs in a port other than the default 3306.
  -   If you aren't sure what this means, the server is likely running in the default port. Don't change this.
  -   Default value - 3306 - **Valid**
- `accessTokenDBName`, `nifty500DBName`, `niftyOptionsDBName` and `bankNiftyOptionsDBName` :
  -   Names used for DBs that will be created for storing the access tokens and tick data
  -   Live tick data will first be stored in a table called `dailytable` in `nifty500DBName`.
  -   You can store all the tables in the same database, as there are no conflicts in the Table Names.
      -   i.e., you can use the same DB Name value for all four fields, and the code will run without issues.
      -   I prefer differentiating these databases for various purposes.
  -   Default values - `zerodha_tokens` , `aws_das_nse`, `aws_das_niftyopt` and `aws_das_bankopt` - **Valid**
- `marketCloseHour` and `marketCloseMinute`:
  -   Determines when the ticker will be stopped.
  -   Used by DAS_main.py. It will proceed to the backup operations after the specified time.
  -   Accept integers in 24-hour format but non-padded numbers.
  -   This is helpful when you want to test the program and stop the ticker at a different time.
  -   You can perform such testing without disturbing the actual code
  -   Default values - `15` and `35` - 3:35 p.m. - **Valid**
- `backupWorkerCount`:
  - Number of parallel workers used by DAS_dailybackup. Default value - 4 - **Valid**
#### 3. Customize lookupTables > lookupTables_Nifty500.csv with additional instruments
  - The lookupTables directory **WILL NOT** be downloaded as it is included in .gitignore. This is to ensure you do not accidentally overwrite any customization when you pull changes from the Repo
  - If you want to add instruments to the lookup, run `python lookupTablesCreator.py` after updating dasConfig.json to let the script create the file.
  - lookupTables > lookupTables_Nifty500.csv is the only persistent list that will automatically be updated (only additions) without removing older instruments.
  - If you wish to subscribe to additional instruments other than Nifty500, Nifty and BankNifty Options, add them to lookupTables_Nifty500.csv
  - Use the existing Symbols and TableNames in the file as a reference.
  - The symbols have to be valid for Zerodha. Use the [Zerodha Instrument Dump](https://api.kite.trade/instruments) to validate
  - Ensure the TableName has no blank spaces or special characters other than `_` (underscore).
  - The TableName will be created in the databases the next time DAS_main.py or lookupTablesCreator.py are run
  - If you haven't provided this file when DAS_main.py is run, nifty500Updater.py as a part of it will create lookupTables_Nifty500.csv
     -  The auto-generated file will contain
        -  Nifty 500 instruments on that day
        -  NIFTY 50 and NIFTY BANK indexes
        -  NIFTY and BANKNIFTY Futures for the current month
#### 4. `pip install -r requirements.txt`

### To Execute:
- `cd ZerodhaWebsocket`
- `python DAS_main.py` or `python3 DAS_main.py`

### But What does it do?:
- For regular activities, just run DAS_main.py. It performs the following actions in sequence.
- All the individual functions will
    - report failures by email.
    - Create their log files under Logs > yyyy-mm-dd_DAS_Logs
- DAS_main.py
  0. isDasConfigDefault.py
        - Check if dasConfig.json has default invalid values
  1. tradeHolidayCheck.py
        - Get Holiday List => getHolidayListFromUpStox (Free and Open). If fail, getHolidayListFromNSE. If Fail, use the local file.
        - Every time getHolidayListFromUpStox or getHolidayListFromNSE is successful, the holiday list is stored locally as tradingHolidays.csv
        - Can be Run standalone - Checks if today is a holiday
        - Return True if the given date is found in the holiday list. Else False.
  2. accessTokenReq.py
        - Gets the access token for the Zerodha API app and stores it in {accessTokenDBName}.kite1tokens
        - Can be Run standalone - Updates latest accessToken in DB
        - Returns True if success. Else False.
        - On Failure :
            - Check if the acccesstoken in the DB was updated after 08:00 today.
                - You could have used manualAccessTokenReq(more on this later) or updated the token some other way
            - If it is fresh, return True but log error and mail
            - Else, retry after 30 seconds - Tries this 5 times
  3. nifty500Updater.py
       - Gets the latest Nifty 500 list from the NSE site.
       - If local-file lookupTables> lookupTables_Nifty500.csv exists:
         - Updates it with new symbols
         - Update NIFTY and BANKNIFTY Futures for the current month if necessary
       - Else:
         - Creates a new file wit
          -  Nifty 500 instruments on that day
          -  NIFTY 50 and NIFTY BANK indexes
          -  NIFTY and BANKNIFTY Futures for the current month
       - All symbol additions will be logged in nifty500_SymbolsChanged.log in the current directory
       - Returns True if success. Else False.
       - Can be Run standalone
  4. lookupTablesCreator.py
        - Downloads [Zerodha Instrument Dump](https://api.kite.trade/instruments)
        - Uses sub-directory lookupTables for storing files
        - 4.1 lookupTablesCreatorNifty500
            - Lists instrument_token for lookupTables_Nifty500.csv and saves it as nifty500TokenList.csv
            - Saves instrument_token for Indexes indexTokenList.csv
            - Creates and Saves instrument_token:TableName dictionary nifty500TokenTableDict.npy - Used by DAS_Ticker to identify DB, Table and tradingsymbol while before storing ticks.
        - 4.2 lookupTablesCreatorNiftyOptions
            - Finds current and next weekly expiry dates for Nifty Options
            - Saves instrument_token list for all Nifty Option instruments for those two expiries as niftyOptionsTokenList.csv
            - Creates and Saves instrument_token:TableName dictionary niftyOptionsTokenTableDict.npy
        - 4.3 lookupTablesCreatorBankOptions
            - Same for BankNifty Options
            - Save instrument_token list bankNiftyOptionsTokenList.csv
            - instrument_token:TableName dictionary bankNiftyOptionsTokenTableDict.npy   
        - 4.4 Create DB `{nifty500DBName}` and dailytable            
        - Returns True if success. Else False.
  5. DAS_Ticker.py
       - Will only proceed if all the previous steps returned True. tradeHolidayCheck should have returned False.
       - Accepts marketCloseHour and marketCloseMinute
       - Starts a countdown timer for self-destruction.
       - Logs into Kite with the latest access token found in {accessTokenDBName}.kite1tokens
       - Gets instrument_tokens from nifty500TokenList.csv, indexTokenList.csv, niftyOptionsTokenList.csv and bankNiftyOptionsTokenList.csv in the lookupTables directory.
       - Subscribes to all of them in FULL mode
       - Receives ticks from Zerodha Websocket.
       - Adds tradingsymbol, tablename and databasename to the ticks and stores them into `{nifty500DBName}`.dailytable.
       - Roughly based on the last suggestion in this discussion - [Delay is websocket streaming
](https://kite.trade/forum/discussion/1674/delay-is-websocket-streaming). I haven't implemented the queue/multi-threaded approach for DB store as I use `REPLACE INTO` to maintain unique timestamps and combining this with multithreading results in deadlocks.
       - See changelog **[2024-04-11](#2024-04-11)** for query examples for dailytable
  7. DAS_dailyBackup.py
       - Checks and reports if any of the tokens in lookupTables_Nifty500.csv did not receive any ticks by the end of the day.
           - This indicates that the corresponding symbol has potentially changed or has been delisted
       - Creates main databases {nifty500DBName}, {niftyOptionsDBName} and {bankNiftyOptionsDBName}.
       - Creates individual tables for all the instrument_tokens in the daily table.
       - Splits and store ticks from the daily table into the individual tables
       - Reports about backup failures.
       - Drops dailytable if all backups were successful.
       - End of DAS_main
       - Returns True if success. Else False.
       - **NOTE**: I feel DAS_dailyBackup is sub-optimal but couldn't find any other way. Please feel free to raise a PR or even an issue if you have a better appraoch for splitting dailytable into the individual tables.
- Other functions used by DAS_main and sub-modules                 
    - DAS_gmailer.py
        - Used to report start, completion and failures in DAS_main
        - On an Ideal day, you would receive two emails - One for the start and one for the completion of DAS_main
    - DAS_attachmentMailer.py
        - Report list of blank tables from lookupTables_Nifty500.csv at EoD
    - DAS_errorLogger.py
        - All functions log their status and failures in their respective log files
        - But DAS_errorLogger is called on all failures, logging any failure from any function in DAS_Errors_yyyy-mm-dd.log
        - It also prints the error in Red (I hope)
- manualAccessTokenReq.py
    - The only automation failure I have faced in the past (almost) 4 years for this project is when Zerodha makes changes in their Login Page
    - This breaks the Selenium automation used for accessTokenreq
    - One of the reasons I had split accessTokenreq to be standalone in the previous version of the project => Fix, Test ,Repeat.
    - In a few occasions, I was able to fix the error and rerun accessTokenreq before the markets open.
    - But if you can't fix accessTokenreq before market hours, run manualAccessTokenReq.py to manually login to the kiteconnect URL and paste the response URL
    - manualAccessTokenReq will then get the accesstoken using the requestToken in the URL you provided
    - If you run DAS_main after this, accesstokenreq will return True if the accestoken is fresh (generated after 08:00 a.m. today) and will
    - In short, on automation failure, you can run manualAccessTokenReq and then rerun das_main

#### Functions outside the scope of DAS_main that I use and are completely optional:
 - sysStartupNotify.py
     - Send an email stating the machine has started.
     - Added as a cronjob to run on startup: `@reboot /usr/bin/python3 /home/ubuntu/ZerodhaWebsocket/sysStartupNotify.py`
 - tradeHolCheck_shutDown.py
     - Check if today is a trading Holiday. Notify and shut the machine down if trading holiday.
     - Added as a cronjob to run at 08:40 a.m., Monday to Friday: `40 8 * * 1-5 /usr/bin/python3 /home/ubuntu/ZerodhaWebsocket/tradeHolCheck_shutDown.py`
 - getExpiryPrefix
     - Generate the prefix for Nifty and BankNifty Option instruments for a given date.
     - Once the prefix is generated, you can add the strike price and CE/PE to it to find the relevant instrument.
     - {getExpiryPrefix(inputDate)}{strikePrice}CE or PE
     - Useful in backtests.
     - Relies on the trading holidays being maintained in the current folder as tradingHolidaysAllYears.csv
     - tradingHolidaysAllYears.csv holds holidays from 2019 to 2024
     - Usage:
          
               from getExpiryPrefix import getExpPrefNifty, getExpPrefBankNifty
               inDate = '2020-01-01'
               print(getExpPrefBankNifty(inDate))
               print(getExpPrefNifty(inDate))
           
  
### **Automation I use outside the provided code:**
- I run the whole thing in an AWS EC2 machine (~~m5.large~~ ~~c6a.xlarge~~ ~~c6a.large~~ t3a.medium) with EBS type gp3 (3000 IOPS)
- I've set up an AWS Lambda function (EventBridge—CloudWatch Events) to start the machine every weekday at 08:30 IST.
- It could start a bit late, even at 09:10 and then DAS_main.py. But I am starting the machine and DAS_main a bit earlier, in case Zerodha or some other component in the pipeline has some breaking change that the code has to adapt to.
  - Instead of running the Python code directly, I have wrapped them inside bash scripts that perform the following:
  - Change directories if needed
  - Start named [tmux](https://github.com/tmux/tmux/wiki) sessions and log the screen output. 
  - Run the corresponding Python code.
    - The named tmux sessions allow me to connect to the machine and switch to the specific job if needed.
    - I am logging the screen (stdout) output in case the websocket or some other part of the code spits out or does something that isn't exactly an exception and hence hasn't been captured by the custom loggers.
    - Startup script I use for DAS_main:
        - startDasMain.sh:

              #!/bin/bash  
              cd /home/ubuntu/ZerodhaWebsocket
              tmux new-session -d -s DASRunning '/usr/bin/python3 -u DAS_main.py  2>&1 | tee -a DAS_Main_ScreenLog.log'
- Cronjob list:
  
      @reboot cd /home/ubuntu/ZerodhaWebsocket/ && /usr/bin/python3 sysStartupNotify.py
      38 8 * * 1-5 cd /home/ubuntu/ZerodhaWebsocket/ && /usr/bin/python3 tradeHolCheck_shutDown.py
      40 8 * * 1-5 /home/ubuntu/startDasMain.sh
      50 15 * * 1-5 /home/ubuntu/dasScripts/dbSizeCheck.sh
      00 16 * * 1-5 sudo poweroff
- dbSizeCheck.sh - Checks disk utilization and DB growth size and notifies me by email. (code not included here)

The only part of this project that is still being done manually is exporting the database from EC2 and importing it to my local machine.  
This has to be done cause AWS EBS is expensive compared to local storage (duh!), and I do this roughly once a month. 
Though I have automated parts of this process (dump in AWS, SCP from Local, import in local, disaster recovery backup to Deep Archive), it has to be triggered manually as the local machine and the EC2 instance might not be running at the same time.

### Changelog:
  #### <ins>**2024-04-11**</ins>:
  - DAS_Ticker - Live tick data is now stored into one table for all ticks. This was to reduce the DB and disk overhead(IOPS) from looping through each tick and storing it in the respective table.
  - The loop and store approach required 1000+ IOPS. This has  been brought down to ~300 IOPS
  - This means querying for a symbol during market hours has to be done differently.
  - Table:
    {nifty500DBName}.dailytable
  - Example queries to get data from live DB (live Ticks):
      - SELECT timestamp, price FROM dailytable WHERE tradingsymbol='NIFTY 50' order by timestamp DESC LIMIT 5;
      - SELECT timestamp, price FROM dailytable WHERE tablename='NIFTY' order by timestamp DESC LIMIT 5;
      - SELECT instrument_token, timestamp, price, volume FROM dailytable WHERE tradingsymbol='NIFTY24APRFUT' order by timestamp DESC LIMIT 5;
      - SELECT timestamp, price, volume FROM dailytable WHERE tablename='NIFTYFUT' order by timestamp DESC LIMIT 5;
      - SELECT timestamp, price, volume FROM dailytable WHERE instrument_token=13368834 order by timestamp DESC LIMIT 5;
  - nifty500DBName configured in dasConfig.json  
  - tradingsymbol, tablename, instrument_token and timestamp columns have indexes in the Table.
  - After marketclose, data from dailytable is copied over to indidvidual tables, filtering on the instrument_token.
  - DAS_Ticker now accepts marketcloseHour and Minute. Killer no longer required and has been removed.  

  #### <ins>**2024-03-27**</ins>:
   - Major revamp of the entire project
   - <ins>**Breaking Changes for existing users**</ins>
       - If you were using the previous version of the project (DAS5,DAS6 and whatnot), firstly, thank you for putting up with the insane naming convention
       - The previous version was not big on versioning for the packages but was actually reliant on specific versions in certain places.  
       - But I have used more recent versions of selenium (4.6) and kiteconnect(5.0.1) to keep the project somewhat futureproof, resulting in breaking changes in a few places.
       - Refer to requirements.txt for the exact versions of the packages required for the current version of the project
       - Selenium 4.6 :
           - Webdriver binary doesn't have to be downloaded and stored locally - Good.
           - Uses driver.find_element(By.XPATH,'xpath_to_find'). Versions before 4 use driver.find_element_by_xpath('xpath_to_find') - Breaking change
       - kiteconnect 5.0.1 (Was using 3. something earlier):
           - kiteConnect ticker field name changes in v4 and later.https://github.com/zerodha/pykiteconnect?tab=readme-ov-file#v4---breaking-changes
           - This meant updating the SQL statements used in the ticker to use different keys from the ticker feed.
           - However, I have retained the same column names for the tables.
           - So if you have other kiteconnect websocket applications that use kiteconnect versions older than 4, either run this in a separate virtualenv or update the SQL statements in DAS_ticker to the old field names
           - Refer to the header in DAS_ticker to know the old field names and the corresponding new ones
   - Uses One Zerodha API app. Was using two earlier
   - One websocket connection for all instruments from Nifty 500, Nifty Weekly options and BankNifty weekly options (was using six earlier)
       - Current and Next week's expiry for Weekly options
   - Config stored in file dasConfig.json (was creds.json)
   - Database names, MySQL port numbers and market close times are now customizable through dasConfig.json
   - The trading holiday list is fetched dynamically on every run
   - Weekly expiry dates for Nifty and BankNifty are fetched dynamically from the Zerodha Instrument dump and don't rely on the tradingHolidays list any more.
  - No longer disconnecting and updating weekly options list to handle huge moves in Indexes
   - Fetching ALL instruments for NIFTY and BANKNIFTY weekly options (current and next week) as opposed to a shortlist earlier
   - nifty500Updater ensures all new Nifty500 instruments are added to the ticker automatically
   - Removed manual toil that was earlier required for maintaining the latest Nifty 500 Instrument list and trading holiday list

### Performance Tweaks:
  - Kite ticker sends ticks as lists of dictionaries.
  - For each batch, DAS_Ticker 
    - converts the list of dictionaries into a Pandas DF
    - preprocesses a bit like generalizing Index ticks to match FULL structure (2 columns vs 47)
    - Adds a couple of columns that will be useful for querying
    - Inserts into a dailytable using a custom DF.to_sql method.
  - This is done in batches as received and needs ~ 300 IOPS 
  - So keep an eye on the Disk I/O wait times to see if there are bottlenecks. If there are, you are likley to see a lag in the ticks stored in the daily table.  
  - Use something like the below query to check for lags DURING MARKET hours. 
  - `SELECT timestamp, instrument_token, tradingsymbol, price from dailytable order by timestamp desc limit 1; SELECT NOW();` There shouldn't be more than a couple of seconds of difference between the timestamp for the latest entry in DB and the current time.
   - Time taken by DAS_dailybackup depends on multiple factors like CPU speed, Memory, Disk I/O limits and throughput. Increasing `backupWorkerCount` wouldn't magically improve performance. 
   - Play around with the following config params in your MySQL/MariaDB config to find the optimal values for DAS_Ticker and DAS_dailybackup:
      - innodb_buffer_pool_size
      - innodb_io_capacity
      - innodb_io_capacity_max
      - innodb_thread_concurrency
      - innodb_flush_log_at_trx_commit
  - DAS_Ticker stores the DBName and Tablename in along with the ticks into `{nifty500DBName}`.dailytable . This is currently not useful for any of the operations (as on 2024-04-17). I have added them there for now, in case I figure out a better approach for DAS_dailybackup .

### Raise Issues:
- I try to catch up with breaking changes from Zerodha or NSE as soon as possible, as I use the same code daily, and my code would also fail.  
- However, my updates weren't fast enough on subtle changes in a few occasions.  
For example, I failed to notice the expiry date changes in BankNifty (Thur to Wed) for almost a month in September 2023.  
- So, if you use this project and come across some change in NSE or Zerodha that might affect the data acquisition in any way, do not hesitate to create an issue in this repo. I'll try to address it if applicable or let you know if it is irrelevant.  
- Feel free to [contact me](https://www.linkedin.com/in/rthennan) for any questions. 
