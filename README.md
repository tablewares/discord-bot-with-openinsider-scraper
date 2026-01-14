# discord-bot-with-openinsider-scraper

A basic discord bot that utilizes the openinsider scraper tool from https://github.com/sd3v/openinsiderData.git to send updates to a specified channel for alerts of new Insider trades.

**Vibe coding Warning:**
Most of the core logic of the bot.py was coded by AI


**Commands**
!start - starts a periodic scanner updating as soon as it finds new information
!stop - stops the scanner
!force - forces an output, disregards history
!status - check if scanner is running
!today - checks for if the trade date is on the current day (rare)
!analysis - outputs three contenders as the best stocks, does not work but im sick of this project and I don't want to fix anything anymore

**How to set up (Discord side)**
If you already have a bot ignore this
Go to: https://discord.com/developers/application
and create a new application

For a discord bot token
In your application, go to the bot tab and copy the token under the token section

To set it up for your server 
In you application, go to the installation tab and copy the url and enter it in your browser
From there, go to "add to server" and select a server that you manage

**Installation Python** <- use first if possible
git clone https://github.com/tablewares/discord-bot-with-openinsider-scraper.git
cd into the directory
create a venv folder: python -m venv venv
activate it
linux: source venv/bin/activate
windows: .\\venv\Scripts\activate

then install the dependencies
pip install -r requirements.txt

Add your channel ids in the bot_config.yaml for the bot to send messages
In the terminal, set a environmental variable named DISCORD_TOKEN to your discord bot token
linux: export DISCORD_TOKEN = <your token>
windows: [Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "<your token>", "User")
For windows environmental variables to work, you have to be in a new session
In a vm, use this to keep the python file even if you close the ssh terminal
nohup python3 bot.py &

**Docker installation** <- Some features will not work, will probably not fix
git clone https://github.com/tablewares/discord-bot-with-openinsider-scraper.git
cd in the directory
docker build -t my_bot .

create a .env file like this
DISCORD_TOKEN=<your token>
DATA=<data channel id>
STATUS=<status channel id>

you can have only one channel id in the env file to send all data to one channel
then run
docker run -env-file .env my_bot


This application works best in a always on vm
Check the data yourself, data format may be messed up and may not even be reliable or true.
Note: a e2 micro vm from google cloud is free, look up proper configurations to get one for free
