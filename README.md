# Cortensor-monitoring-app
v3 monitoring app.

ui improvements
telegram push notifications
basic miner monitoring
stat collection to be used with future releases

linux needs to run in a venv with certain python dependencies installed. copy existing miners.json to dl folder. run with python3 main.py

sudo apt update
sudo apt install python3-venv python3-pip
python3 -m venv cortensor
source cortensor/bin/activate
pip install pyqt5 web3 requests logging

windows, extract and add existing miners.json file to folder if existing.

telegram needs following to work, search for botfather, run /newbot this will give you the bot token. then search for userinfobot run /start this will give you the id. add these to the fields in alert bot tab, check enable alerts and send test message.

eth threshold settings are for display on dashboard only.

stats bot option compare over time will show performance change for selected metrics. enable stats bot for hourly or user selected time interval notifications to telegram
