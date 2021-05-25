#!/bin/bash
python3 run_ipc.py &

while true
do
    python3 run_bot.py

    echo "Hit CTRL+C to shutdown."
    sleep 3s
done