#!/bin/bash

# Запрашивает пароль через rofi и подключается к Wi-Fi сети

SSID="$1"

password=$(rofi -dmenu -password \
    -p "Пароль для $SSID" \
    -theme-str 'listview { lines: 0; }' \
    -theme-str 'inputbar { children: [prompt, entry]; }')

[ -z "$password" ] && exit 0

~/.config/my_eww/scripts/connect_wifi.sh "$SSID" "new" "$password"
