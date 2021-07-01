#!/bin/bash
$1 app/i18n/generate_mo
$1 update_db.py

$1 run_ipc.py &
$1 run_dashboard.py &

while true
do
    $1 update_db.py
    $1 app/i18n/generate_mo
    $1 run_bot.py

    echo "Hit CTRL+C to shutdown."
    sleep 3s
done