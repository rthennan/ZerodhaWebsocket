# Zerodha Websocket
Acquire and store tick data for NSE (India) stocks, Index Futures and Index Options from Zerodha.  
  
 ### **Pre-requisites:**
- Active subscription for [Kite Connect API](https://developers.kite.trade/apps).
- Python3 with packages listed under the tools section
- MySQL / MariaDB Server
- Zerodha, gmail and MySQL credentials have to be filled in dasConfig.json file
  - Storing passwords and keys in a plaintext file is a potential security issue.
  - This is used for simplicity. Please consider switching to a more secure secret management system in Production deployments
### **Tools primarily used:**
- Python
  - Pandas - For handling CSV and Excel Files
  - Selenium - Automate Kite Authentication and getHolidayList from NSE
  - MySQLdb
  - numpy - just for saving lists and dictionaries. Pickle could have been used
  - shutil - handling files
  - smtplib - Mail notification using Gmail
  - pyotp - for generating TOTP requried for Zerodha authentication
  - json - for storing and accessing credentials, api keys, etc. (creds.json)
- MariaDB /MySQL Server for storing tick data

### Setup/Installation :
- Install Python3
- Install MySQL / MariaDB Server
- MySQL Client
-   For windows: https://stackoverflow.com/questions/34836570/how-do-i-install-and-use-mysqldb-for-python-3-on-windows-10
-   For Linux  
    `sudo apt-get update`  
    `sudo apt-get install libmysqlclient-dev libmariadb-dev`  
-   Install Google Chrome
-     For Linux:
      wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
      sudo dpkg -i google-chrome-stable_current_amd64.deb
- Ensure you have installed the MySQL client packages at the OS level. Else pip install wil fail for mysqlclient
- `pip install -r requirements.txt`

### Update dasConfig.json:
- Doc in Progress

### To Execute:
- Just run `python DAS_main.py`

### Detailed Notes:
- Doc in Progress
  
  


  
### **Automation I use outside the provided code:**
- I run the whole thing in an AWS EC2 machine (~~m5.large~~ c6a.xlarge)
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

The only part of this project, other than the yearly activity still being done manually, is exporting the database from AWS and importing it to my local machine.  
This has to be done cause AWS EBS is expensive compared to local storage (duh!), and I do this roughly once a month. 
Though I have automated parts of this process (dump in AWS, SCP from Local, import in local), it has to be triggered manually as the local machine and the AWS instance might not be running at the same time.

I started this project with hopes of building a trading bot.  
Specifically, the least recommended approach - Intraday Trading on Naked Index Options for Nifty and BankNifty.
The attempts failed of course. More details on the Failed Approach can be found in the [timeSeriesFail](https://github.com/rthennan/timeSeriesFail) Repo.

Feel free to [contact me](https://www.linkedin.com/in/rthennan) for questions if any. 

### **To Do:**   
Reorganize names for DBs, tables, logs and access tokens. DAS<X> is inconsistent and all over the place.
