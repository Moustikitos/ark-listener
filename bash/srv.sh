#!/bin/bash
. ~/.local/share/ark-listener/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-listener
gunicorn --bind=0.0.0.0:5001 --workers=5 lystener.app:app --access-logfile -
deactivate
exit