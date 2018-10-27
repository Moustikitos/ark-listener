
# install system dependencies
clear
echo installing system dependencies
echo ==============================
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip

# download ark-listener package
echo
echo downloading ark-listener package
echo ================================
cd ~
if ! (git clone https://github.com/Moustikitos/ark-listener.git) then
    cd ~/ark-listener
    git fetch --all
    git reset --hard origin/master
else
    cd ~/ark-listener
fi

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install --user -r requirements.txt -q

# initialize lystener
echo
echo initializing lystener
echo =====================
cp lys ~
cd ~
chmod +x lys

# launch lystener-server or reload it
echo
echo launching/restarting pm2 tasks
echo ==============================
if [ "$(pm2 id lystener-server) " = "[] " ]; then
    cd ~/ark-listener
    pm2 start app.json
else
    pm2 restart lystener-server
fi
