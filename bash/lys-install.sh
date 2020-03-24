
# install system dependencies
clear

if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "branch selected = $B"

echo
echo installing system dependencies
echo ==============================
sudo apt-get -qq install python python-dev
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip
sudo apt-get -qq install python3 python3-dev
sudo apt-get -qq install python3-setuptools
sudo apt-get -qq install python3-pip
sudo apt-get -qq install pypy
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
    echo "ark-zen already cloned !"
fi
cd ~/ark-listener
git reset --hard
git fetch --all
if [ "$B" == "master" ]; then
    git checkout $B -f
else
    git checkout tags/$B -f
fi
git pull
echo "done"

echo
echo creating virtual environment
echo =============================

if [ -d "$HOME/.local/share/ark-listener/venv" ]; then
    read -p "remove previous virtual environement ? [y/N]> " r
    case $r in
    y) rm -rf ${HOME}/.local/share/ark-listener/venv;;
    Y) rm -rf ${HOME}/.local/share/ark-listener/venv;;
    *) echo -e "previous virtual environement keeped";;
    esac
fi

if [ ! -d "$HOME/.local/share/ark-listener/venv" ]; then
    echo -e "select environment:\n  1) python3\n  2) pypy"
    read -p "[default:python]> " n
    case $n in
    1) TARGET="$(which python3)";;
    2) TARGET="$(which pypy)";;
    *) TARGET="$(which python)";;
    esac
    mkdir ~/.local/share/ark-listener/venv -p
    virtualenv -p ${TARGET} ~/.local/share/ark-listener/venv -q
fi

. ~/.local/share/ark-listener/venv/bin/activate
export PYTHONPATH=${HOME}/ark-listener
cd ~/ark-listener
echo "done"

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install -r requirements.txt -q
echo "done"

chmod +x bash/activate
cp bash/lys ~
cd ~
chmod +x lys

echo
echo "setup finished"
