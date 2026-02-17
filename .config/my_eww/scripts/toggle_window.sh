#!/bin/bash

# Переключает popup окно: закрывает если открыто, открывает если закрыто.
# При открытии закрывает все остальные popup'ы.

EWW="eww -c /home/laxerem/.config/my_eww"
WINDOW="$1"
ALL_POPUPS="volume-popup wifi-popup"

# Проверяем, открыто ли окно
if $EWW active-windows 2>/dev/null | grep -q "^${WINDOW}:"; then
    $EWW close "$WINDOW"
    # Сбрасываем состояние wifi при закрытии
    if [ "$WINDOW" = "wifi-popup" ]; then
        $EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password=''
    fi
else
    # Закрываем все остальные popup'ы
    for p in $ALL_POPUPS; do
        if [ "$p" != "$WINDOW" ]; then
            $EWW close "$p" 2>/dev/null
            if [ "$p" = "wifi-popup" ]; then
                $EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password='' 2>/dev/null
            fi
        fi
    done
    $EWW open "$WINDOW"
fi
