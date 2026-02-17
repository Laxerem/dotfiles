#!/bin/bash

# Открывает popup, закрывая все остальные.
# Использование: open_popup.sh <имя_окна>

EWW="eww -c /home/laxerem/.config/my_eww"
WINDOW="$1"
ALL_POPUPS="volume-popup wifi-popup"

for p in $ALL_POPUPS; do
    if [ "$p" != "$WINDOW" ]; then
        $EWW close "$p" 2>/dev/null
        # Сбрасываем wifi-переменные при закрытии wifi-popup
        if [ "$p" = "wifi-popup" ]; then
            $EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password='' 2>/dev/null
        fi
    fi
done

$EWW open "$WINDOW" 2>/dev/null
