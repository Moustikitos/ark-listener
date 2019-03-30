
# install system dependencies
clear

if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "branch selected = $B"

echo installing system dependencies
echo ==============================
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx

# download ark-listener package
echo
echo downloading ark-listener package
echo ================================
cd ~
if (git clone --branch $B https://github.com/Moustikitos/ark-listener.git) then
    cd ~/ark-listener
else
    cd ~/ark-listener
    git reset --hard
fi
git fetch --all
if [ "$B" == "master" ]; then
    git checkout $B -f
else
    git checkout tags/$B -f
fi
git pull

echo
echo creating virtual environement
echo =============================
mkdir ~/.local/share/ark-listener/venv -p
virtualenv ~/.local/share/ark-listener/venv -q
. ~/.local/share/ark-listener/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-listener
export PATH=$(yarn global bin):$PATH
cd ~/ark-listener

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install -r requirements.txt -q

# # initialize lystener
# echo
# echo initializing lystener
# echo =====================
# cp lystener/lys.py ~/lys
# cd ~
# chmod +x lys

# # # launch lystener-server or reload it
# echo
# echo launching/restarting pm2 tasks
# echo ==============================
# if [ "$(pm2 id lys-srv) " = "[] " ]; then
#     cd ~/ark-listener
#     pm2 start app.json
# else
#     pm2 restart lystener-server
# fi
