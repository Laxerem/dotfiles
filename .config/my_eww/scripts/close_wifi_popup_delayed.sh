#!/bin/bash

# Закрывает wifi-popup с задержкой, проверяя реальную позицию курсора.

EWW="eww -c /home/laxerem/.config/my_eww"
BAR_HEIGHT=35

sleep 0.3

# Не закрываем, если пользователь вводит пароль
if [ "$($EWW get wifi_show_password)" = "true" ]; then
    exit 0
fi

# Получаем позицию курсора через hyprctl
CURSOR_JSON=$(hyprctl cursorpos -j 2>/dev/null)
CX=$(echo "$CURSOR_JSON" | jq -r '.x' 2>/dev/null)
CY=$(echo "$CURSOR_JSON" | jq -r '.y' 2>/dev/null)

# Если hyprctl недоступен — fallback на wifi_hover
if [ -z "$CX" ] || [ "$CX" = "null" ]; then
    if [ "$($EWW get wifi_hover)" = "false" ]; then
        $EWW close wifi-popup 2>/dev/null
        $EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password=''
    fi
    exit 0
fi

# Курсор на баре (верхние 35px экрана) — не закрываем
if [ "$CY" -lt "$BAR_HEIGHT" ] 2>/dev/null; then
    exit 0
fi

# Получаем границы окна wifi-popup
POPUP_JSON=$(hyprctl clients -j 2>/dev/null | jq 'first(.[] | select(.title == "wifi-popup"))' 2>/dev/null)
if [ -n "$POPUP_JSON" ] && [ "$POPUP_JSON" != "null" ]; then
    PX=$(echo "$POPUP_JSON" | jq -r '.at[0]')
    PY=$(echo "$POPUP_JSON" | jq -r '.at[1]')
    PW=$(echo "$POPUP_JSON" | jq -r '.size[0]')
    PH=$(echo "$POPUP_JSON" | jq -r '.size[1]')

    if [ -n "$PX" ] && [ "$PX" != "null" ]; then
        PR=$((PX + PW))
        PB=$((PY + PH))
        # Курсор внутри popup — не закрываем
        if [ "$CX" -ge "$PX" ] && [ "$CX" -le "$PR" ] && \
           [ "$CY" -ge "$PY" ] && [ "$CY" -le "$PB" ] 2>/dev/null; then
            exit 0
        fi
    fi
fi

$EWW close wifi-popup 2>/dev/null
$EWW update wifi_show_password=false wifi_connect_ssid='' wifi_password=''
