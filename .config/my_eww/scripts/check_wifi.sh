#!/bin/bash
# Получаем имя сети, если подключено
ssid=$(iwgetid -r)
if [ -z "$ssid" ]; then
    echo "Без интернета"
else
    echo "$ssid"
fi