#!/bin/bash

# Скрипт для подключения к Wi-Fi сети

SSID="$1"
MODE="$2"  # "saved" для сохраненных сетей
PASSWORD="$3"  # Пароль (опционально, для новых сетей)

if [ -z "$SSID" ]; then
    notify-send "Wi-Fi Error" "Не указано имя сети"
    exit 1
fi

# Если режим "saved" - подключаемся к сохраненной сети
if [ "$MODE" = "saved" ]; then
    notify-send "Wi-Fi" "Подключение к $SSID..."
    if nmcli connection up "$SSID" 2>/dev/null; then
        notify-send "Wi-Fi" "Успешно подключено к $SSID"
    else
        notify-send "Wi-Fi Error" "Не удалось подключиться к $SSID"
    fi
    exit 0
fi

# Для новых сетей - подключаемся с паролем
if [ -n "$PASSWORD" ]; then
    notify-send "Wi-Fi" "Подключение к $SSID..."
    if nmcli device wifi connect "$SSID" password "$PASSWORD" 2>/dev/null; then
        notify-send "Wi-Fi" "Успешно подключено к $SSID"
        # Сбрасываем переменные в EWW
        eww -c /home/laxerem/.config/my_eww/ update wifi_show_password=false
        eww -c /home/laxerem/.config/my_eww/ update wifi_connect_ssid=''
        eww -c /home/laxerem/.config/my_eww/ update wifi_password=''
    else
        notify-send "Wi-Fi Error" "Не удалось подключиться к $SSID. Проверьте пароль."
    fi
else
    notify-send "Wi-Fi Error" "Пароль не указан"
fi
