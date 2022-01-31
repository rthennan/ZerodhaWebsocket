# Zerodha Websocket
Acquire and store tick data for NSE (India) stocks, Index Futures and Index Options from Zerodha.  
  
 ### **Pre-requisites:**
- Active subscription for [Kite Connect API](https://developers.kite.trade/apps).
- Python3 with packages listed under the tools section
- MySQL / MariaDB
- Zerodha, email and MySQL credentials have to be filled in creds.json file
  - Storing passwords and keys in a plaintext file is a potential security issue.  But I can work with this cause the server that I am running the program from is quite secure and isn't open for any incoming connections. So please consider a different approach for credential store if you are running this code from a machine open for incoming connections.

### **Tools primarily used:**
- Python
  - Pandas - For handling CSV and Excel Files
  - Selenium - Automate Authentication
  - MySQLdb
  - numpy - just for saving lists and dictionaries. Pickle could have been used
  - shutil - handling files
  - smtplib - Mail notification
  - pyotp - for generating TOTP requried for Zerodha authentication
  - json - for storing and accessing credentials, api keys, etc. (creds.json)
- MariaDB
- A few XLSX and CSV files to provide the shortlist manually and to keep a track of things.  

  

### **I have split the data acquisition into two sub-parts:**
1. DAS5 - NIFTY, BANKNIFTY, their current month futures and all NIFTY 500 stocks.
2. DAS6 - Weekly Options for Nifty and BankNifty.  

### **API Key and API Sceret:**
- Zerodha's websocket allows subscribing to a maximum of 200 instruments per connection and a maximum of 3 connections are allowed per 'API App'(in other words, one subscription).
- 200 x 3 => 600 instruments max / API App.
- So I use two Zerodha API apps. DAS5 and DAS6 share these in some places.
- **DAS5_tickerV1 , DAS6_NFO_Full_V1 and DAS6_BNFO_Full_V1 - Use ApiKey1 and ApiSec1.**
- **DAS5_2_tickerV1, DAS5_3_tickerV1 and DAS5_4_tickerV1 - Use ApiKey2 and ApiSec2.**
- As you might use just part of thise code, please check and replace the ApiKey and ApiSecret placeholders
  
### **The Process can be split into a few steps:**
1. Shortlist the desired instruments. - Manually Provided for DAS5. Even this piece is autmated in DAS6.
2. Finalize the instrument_tokens (internal codes) for the desired instruments.
3. Fetch the request token and access tokens for Zerodha Kite API. (Automated with Python + Selenium)
4. Connect to [Zerodha's Websocket API](https://kite.trade/docs/connect/v3/websocket/), using the access Token fetched earlier and start receiving tick data.
5. Subscribe to the shortlisted instrument_tokens in the Zerodha Kite's Websocket.
6. Store the received tick data for each stock/index/option into its corresponding 'Daily' table.
  - Since we might receive multiple ticks for the same second, I use the received tick's timestamp as the key and store the streaming data using 'REPLACE INTO' instead of just an insert.
 7. Stop the connection at 15:35 IST. (NSE markets close at 15:30 IST)
 8. Cleanup data from the Daily tables , store the data into the master database and delete the Daily tables.
  - Maintaining a smaller 'Daily' tables improves the 'replace into' performance, compared to storing everything directly to a main database.
  - Data in the daily tables will be minimal, allowing the cleanup to be faster and focused to just one date.

Steps 1 and 2 - lookupIns.py (LookUp Instrument) for DAS5. DAS6 uses a different approach.
Step 3 - accessTokenReq.py  and accessTokenReqDAS6 
Steps 4 to 8 - slightly different between DAS5 and DAS6
  
### **Yearly Activity:**  
DAS6 collects tick data for Nifty and BankNifty weekly options, for the current and next week's expiry.
\DAS6\expiryGenerator\expSuffGenerator.py has to be run before the beginning of every year, for generating that year's weekly expire prefixes.  
Check DAS6's readme to know more.
  
### **Notes:**
- I was initially running this from a local Windows machine. But that failed a few days due to power outages and internet issues. 
  So I moved the code to an AWS instance running Ubuntu. As a positive side effective, I had to migrate the windows specific parts of the code to be more generic.
  Hence the program will run on both Windows and Linux (can't comment on Mac), as long as the pre-requisities mentioned ealier are met.
- My Python skills were quite basic when I started this project.
- My skills improved over time and I started writing better code (I think??) and automated the tasks one by one.
- So you might see a combination of sub-par and decent code in here. 
- I haven't bothered refactoring or improving the code much cause <img src="https://c.tenor.com/fJAoBHWymY4AAAAC/do-not-touch-it-programmer.gif" alt="If the code works, don't touch it" style="height: 200px; width:200px;"/>
  
### **Automation I use outside the provided code:**
- I run the whole thing in an AWS EC2 machine (m5.large)
- I've setup an AWS Lambda function (EventBridge - CloudWatch Events) to start the machine every weekday at 08:30 IST .
  - Instead of running the Python code directly, I have wrapped them inside bash scripts that perform the following:
  - Change directories if needed
  - Start named [tmux](https://github.com/tmux/tmux/wiki) sessions and log the screen output. 
  - Run the corresponding Python code.
    - The named tmux sessions allow me to connect to the machine and switch to the specific job if needed.
    - I am logging the screen (stdout) output in case the websocket or someother part of the code spits or does something that isn't exactly an exception
    - For example, das5TMuxAuto.sh :  
![image](https://user-images.githubusercontent.com/38931343/151724720-9dc71e02-ca09-44a2-a1e4-b1424840237c.png)
   
- Cronjob list from the instance:  
![image](https://user-images.githubusercontent.com/38931343/151722312-6de3b807-8ab2-4bba-98a7-7ef9e4395996.png)
  - Startup Notify - Sends me an email when the machine powers On
  - holCheck - Shuts the instance down if today is a trading holiday
  - das5AccessToken - Runs accessTokenReq.py and accessTokenReqDAS6.py to fetch the access tokens
  - das5TMuxAuto - Starts DAS5/DAS5_MasterV1.py
  - das6TMuxAuto - Starts DAS6/DAS6_MasterV1.py 
  - dbSizeCheck - Checks disk utilization and DB growth size and notifies me by email.(code not included in here)

The only part of this project other than the yearly activity that is still being done manually, is exporting the database from AWS and importing it to my local machine.  
This has to be done cause AWS EBS is expensive compared to localstorage (duh!) and I do this roughly once a month. 
Though I have automated parts of this process (dump in AWS, SCP from Local, import in local), it has to be trigerred manually as the local machine and the AWS instance might not be running at the same time.

I started this project with hopes of building a trading bot.  
Specifically, the least recommended approach - Intraday Trading on Naked Index Options for Nifty and BankNifty.
The attempts failed of course. More details on the Failed Approach can be found in the [timeSeriesFail](https://github.com/rthennan/timeSeriesFail) Repo.

Feel free to [contact me](https://www.linkedin.com/in/rthennan) for questions if any. 

