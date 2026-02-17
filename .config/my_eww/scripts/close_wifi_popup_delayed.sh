#!/bin/bash

# Закрывает wifi-popup с задержкой, если курсор не вернулся.
# Не закрывает попап, если пользователь вводит пароль.

EWW="eww -c /home/laxerem/.config/my_eww"

sleep 0.3

# Не закрываем, если пользователь вводит пароль
if [ "$($EWW get wifi_show_password)" = "true" ]; then
    exit 0
fi

if [ "$($EWW get wifi_hover)" = "false" ]; then
    $EWW close wifi-popup 2>/dev/null
    # Сбрасываем wifi-переменные при закрытии
    $EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password=''
fi
