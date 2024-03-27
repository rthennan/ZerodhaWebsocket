# Zerodha Websocket for Nifty500, Nifty Options and BankNifty Options
Acquire and store tick data for NSE (India) stocks, Index Futures and Index Options from Zerodha.  
DAS - Data Acquisition System. That is what I am calling it.

 ### **Pre-requisites:**
- An active subscription for at least one [Kite Connect API](https://developers.kite.trade/apps) app.
- Python3
- MySQL / MariaDB Server
- Gmail account with App password configured - [Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en)
- Zerodha, Gmail and MySQL credentials have to be filled in the dasConfig.json file
  - Storing passwords and keys in a plaintext file is a potential security issue.
  - This is used for simplicity. Please consider switching to more secure secret management options (like environment variables) for production deployments.
  - All calls for reading dasConfig.json and using the json would have to be updated.
 
### **Tools/Packages primarily used:**
- Pandas - For handling CSV and Excel Files
- Selenium - Automate Kite Authentication and getHolidayList from NSE
- MySQLdb/MariaDB for persistent store of ticker data
- numpy - For saving token lists and dictionaries for ticker subscriptions and stores. Pickle could have been used
- shutil - handling files
- smtplib - Mail notification using Gmail
- pyotp - for generating TOTP required for Zerodha authentication
- json - for storing and accessing credentials, API keys, etc. (dasConfig.json)

### OS Supported:
- Tested in Windows (10 and 11) and Linux (Ubuntu)
- Should work in other Linux Distros as well. The steps for installing MySQL Client and Google Chrome will be different
- I don't see why it wouldn't work on MacOS. But NOT tested.

### Setup/Installation :
- Install Python3
- Install MySQL / MariaDB Server
- MySQL Client
    -   For Windows: https://stackoverflow.com/questions/34836570/how-do-i-install-and-use-mysqldb-for-python-3-on-windows-10
    -   For Linux  
        `sudo apt-get update`  
        `sudo apt-get install libmysqlclient-dev libmariadb-dev`  
-   Install Google Chrome
    - For Linux
        - `wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`
        - `sudo dpkg -i google-chrome-stable_current_amd64.deb`
- Ensure you have installed the MySQL client packages at the OS level. Else, pip install will fail for mysqlclient
- `pip install -r requirements.txt`

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
  -   MariaDB / MySQLDB connection details.
  -   Default values - **Invalid**
- `mysqlPort` :
  -   Update this if your DB Server runs in a port other than the default 3306.
  -   If you aren't sure what this means, the server is likely running in the default port. Don't change this.
  -   Default value - 3306 - **Valid**
- `accessTokenDBName`, `nifty500DBName`, `niftyOptionsDBName` and `bankNiftyOptionsDBName` :
  -   Names used for DBs that will be created for storing the access tokens and tick data
  -   For tick data, a **daily** database, with suffix _daily will be created.
  -   The daily databases will then be dumped to corresponding main databases without the _daily suffix.
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
### To Execute:
- `cd ZerodhaWebsocket`
- `python DAS_main.py` or `python3 DAS_main.py`

### But What does it do?:
- For regular activities, just run DAS_main.py. It performs the following actions in sequence.
- All the individual functions will
    - report failures by email.
    - Create their log files under Logs > yyyy-mm-dd_DAS_Logs
- DAS_main.py
  1. tradeHolidayCheck.py
        - Get Holiday List => getHolidayListFromUpStox (Free and Open). If fail, getHolidayListFromNSE. If Fail, use the local file.
        - Every time getHolidayListFromUpStox or getHolidayListFromNSE is successful, the holiday list is stored locally as tradingHolidays.csv
        - Can be Run standalone - Checks if today is a holiday
        - Return True if the given date is found in the holiday list. Else False.
  2. accessTokenReq.py
        - Gets the access token for the Zerodha API app and stores it in {accessTokenDBName}.kite1tokens
        - Can be Run standalone - Updates latest accessToken in DB
        - Returns True if success. Else False.
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
            - Creates and Saves instrument_token:TableName dictionary nifty500TokenTable.npy - Used by ticker to identify which DB, Table and SQL statement should be used to store the tick data
            - Creates {nifty500DBName}_daily Database and Tables Nifty 500 Instruments
        - 4.2 lookupTablesCreatorNiftyOptions
            - Finds current and next weekly expiry dates for Nifty Options
            - Saves instrument_token list for all Nifty Option instruments for those two expiries as niftyOptionsTokenList.csv
            - Creates and Saves instrument_token:TableName dictionary niftyOptionsTokenTable.npy
            - Creates {niftyOptionsDBName}_daily Database and Tables for Nifty Option Instruments
        - 4.3 lookupTablesCreatorBankOptions
            - Same for BankNifty Options
            - Save instrument_token list bankNiftyOptionsTokenList.csv
            - instrument_token:TableName dictionary bankNiftyOptionsTokenTable.npy
            - Creates {bankNiftyOptionsDBName}_daily Database and Tables for BankNifty Option Instruments      
        - Returns True if success. Else False.
  5. DAS_Ticker.py (run async using multiprocessing)
       - Will only proceed if all the previous steps returned True. tradeHolidayCheck should have returned False.
       - Logs in to Kite with the latest access token found in {accessTokenDBName}.kite1tokens
       - Gets instrument_tokens from nifty500TokenList.csv, indexTokenList.csv, niftyOptionsTokenList.csv and bankNiftyOptionsTokenList.csv in the lookupTables directory.
       - Subscribes to all of them in FULL mode
       - Uses nifty500TokenTable.npy, niftyOptionsTokenTable.npy and bankNiftyOptionsTokenTable.npy to identify the tables to which the tick data should be stored
       - Uses different SQL statements for Indexes and the rest of the instruments as Index ticks have fewer columns.
  6. DAS_Killer.py > killer
       - Count-down timer that runs till `marketCloseHour` and `marketCloseMinute`
       - Once this completes, the execution flow is back to DAS_main, killing the DAS_Ticker process
  7. DAS_dailyBackup.py
       - Checks and reports if any of the tables in lookupTables_Nifty500.csv are empty at the end of the day.
           - This indicates that the corresponding symbol has potentially changed or has been delisted
       - Creates main databases {nifty500DBName}, {niftyOptionsDBName} and {bankNiftyOptionsDBName} . (No _daily suffix)
       - Copies all tables from the _daily databases to their corresponding main database and drops the tables in the _daily DBs
       - Reports about backup failures.
       - End of DAS_main
       - Returns True if success. Else False.  
Other functions used by DAS_main and sub-modules        
- DAS_gmailer.py
    - Used to report start, completion and failures in DAS_main
    - On an Ideal day, you would receive two emails - One for the start and one for the completion of DAS_main
- DAS_attachmentMailer.py
    - Report list of blank tables from lookupTables_Nifty500.csv at EoD
- DAS_errorLogger.py
    - All functions log their status and failures in their respective log files
    - But DAS_errorLogger is called on all failures, logging any failure from any function in DAS_Errors_yyyy-mm-dd.log
    - It also prints the error in Red (I hope)

#### Scripts outside the scope of DAS_main that I use and are completely optional:
 - sysStartupNotify.py
     - Send an email stating the machine has started.
     - Added as a cronjob to run on startup: `@reboot /usr/bin/python3 /home/ubuntu/ZerodhaWebsocket/sysStartupNotify.py`
 - tradeHolCheck_shutDown.py
     - Check if today is a trading Holiday. Notify and shut the machine down if trading holiday.
     - Added as a cronjob to run at 08:40 a.m., Monday to Friday: `38 8 * * 1-5 /usr/bin/python3 /home/ubuntu/ZerodhaWebsocket/sysStartupNotify.py`        

### Breaking changes for existing users
- Doc in Progress
  
### **Automation I use outside the provided code:**
- I run the whole thing in an AWS EC2 machine (~~m5.large~~ c6a.xlarge)
- I've setup an AWS Lambda function (EventBridge - CloudWatch Events) to start the machine every weekday at 08:30 IST .
  - Instead of running the Python code directly, I have wrapped them inside bash scripts that perform the following:
  - Change directories if needed
  - Start named [tmux](https://github.com/tmux/tmux/wiki) sessions and log the screen output. 
  - Run the corresponding Python code.
    - The named tmux sessions allow me to connect to the machine and switch to the specific job if needed.
    - I am logging the screen (stdout) output in case the websocket or some other part of the code spits or does something that isn't exactly an exception
    - For example, das5TMuxAuto.sh :  
![image](https://user-images.githubusercontent.com/38931343/151724720-9dc71e02-ca09-44a2-a1e4-b1424840237c.png)
   
- Cronjob list from the instance:  
![image](https://user-images.githubusercontent.com/38931343/151722312-6de3b807-8ab2-4bba-98a7-7ef9e4395996.png)
  - Startup Notify - Sends me an email when the machine powers On
  - holCheck - Shuts the instance down if today is a trading holiday
  - das5AccessToken - Runs accessTokenReq.py and accessTokenReqDAS6.py to fetch the access tokens
  - das5TMuxAuto - Starts DAS5/DAS5_MasterV1.py
  - das6TMuxAuto - Starts DAS6/DAS6_MasterV1.py 
  - dbSizeCheck - Checks disk utilization and DB growth size and notifies me by email.(code not included here)

The only part of this project that is still being done manually is exporting the database from EC2 and importing it to my local machine.  
This has to be done cause AWS EBS is expensive compared to local storage (duh!), and I do this roughly once a month. 
Though I have automated parts of this process (dump in AWS, SCP from Local, import in local, master backup to Deep Archive), it has to be triggered manually as the local machine and the EC2 instance might not be running at the same time.

Feel free to [contact me](https://www.linkedin.com/in/rthennan) for any questions. 
