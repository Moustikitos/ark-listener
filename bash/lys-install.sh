#!/bin/bash

VENVDIR="$HOME/.local/share/ark-listener/venv"
GITREPO="https://github.com/Moustikitos/ark-listener.git"

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
sudo apt-get -qq install python3 python3-dev python3-setuptools python3-pip
sudo apt-get -qq install pypy3
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx
echo "done"

echo
echo downloading ark-listener package
echo ================================

cd ~
if (git clone --branch $B $GITREPO) then
    echo "package cloned !"
else
    echo "package already cloned !"
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

if [ -d $VENVDIR ]; then
    read -p "remove previous virtual environement ? [y/N]> " r
    case $r in
    y) rm -rf $VENVDIR;;
    Y) rm -rf $VENVDIR;;
    *) echo -e "previous virtual environement keeped";;
    esac
fi

if [ ! -d $VENVDIR ]; then
    echo -e "select environment:\n  1) python3\n  2) pypy3"
    read -p "[default:python3]> " n
    case $n in
    1) TARGET="$(which python3)";;
    2) TARGET="$(which pypy3)";;
    *) TARGET="$(which python3)";;
    esac
    mkdir $VENVDIR -p
    virtualenv -p $TARGET $VENVDIR -q
fi

echo "done"
# if [ $(which pypy3) ]; then echo "OK"; fi

# install python dependencies
echo
echo installing python dependencies
echo ==============================
. $VENVDIR/bin/activate
export PYTHONPATH=$HOME/ark-listener
cd ~/ark-listener
pip install -r requirements.txt -q
echo "done"

chmod +x bash/activate

cp bash/lys ~
cd ~
chmod +x lys

echo
echo "setup finished"
