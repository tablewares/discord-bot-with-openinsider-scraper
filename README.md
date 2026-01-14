# Discord bot with openinsider scraper

A basic discord bot that utilizes the openinsider scraper tool from https://github.com/sd3v/openinsiderData.git to send updates to a specified channel for alerts of new Insider trades.

**Vibe coding Warning:**<br>
Most of the core logic of the bot.py was coded by AI


**Commands**<br>
!start - starts a periodic scanner updating as soon as it finds new information<br>
!stop - stops the scanner<br>
!force - forces an output, disregards history<br>
!status - check if scanner is running<br>
!today - checks for if the trade date is on the current day (rare)<br>
!analysis - outputs three contenders as the best stocks, does not work as intended but whatever

**How to set up (Discord side)**<br>
If you already have a bot ignore this<br>
Go to: https://discord.com/developers/application<br>
and create a new application

For a discord bot token<br>
In your application, go to the bot tab and copy the token under the token section<br>

To set it up for your server<br>
In you application, go to the installation tab and copy the url and enter it in your browser<br>
From there, go to "add to server" and select a server that you manage<br>

**Installation Python** <- use first if possible<br>
git clone https://github.com/tablewares/discord-bot-with-openinsider-scraper.git<br>
cd into the directory<br>
create a venv folder: python -m venv venv<br>
activate it<br>
linux: source venv/bin/activate<br>
windows: .\\venv\Scripts\activate

then install the dependencies<br>
pip install -r requirements.txt

Add your channel ids in the bot_config.yaml for the bot to send messages<br>
In the terminal, set a environmental variable named DISCORD_TOKEN to your discord bot token<br>
linux: export DISCORD_TOKEN = <your token><br>
windows: [Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "<your token>", "User")<br>
For windows environmental variables to work, you have to be in a new session<br>
In a vm, use this to keep the python file even if you close the ssh terminal<br>
nohup python3 bot.py &

**Docker installation** <- Some features will not work, will probably not fix<br>
git clone https://github.com/tablewares/discord-bot-with-openinsider-scraper.git<br>
cd in the directory<br>
docker build -t my_bot .<br>

create a .env file like this<br>
DISCORD_TOKEN=(your token)<br>
DATA=(data channel id)<br>
STATUS=(status channel id)<br>

you can have only one channel id in the env file to send all data to one channel<br>
then run<br>
docker run -env-file .env my_bot<br>


This application works best in a always on vm<br>
Check the data yourself, data format may be messed up and may not even be reliable or true.<br>
Note: a e2 micro vm from google cloud is free, look up proper configurations to get one for free 

