#!/bin/bash
trap "kill 0" EXIT

python3 run_ipc.py &
python3 run_dashboard.py &

while true
do
    python3 run_bot.py

    echo "Hit CTRL+C to shutdown."
    sleep 3s
done