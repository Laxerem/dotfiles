#!/bin/bash

# Проверяем, есть ли среди активных подключений тип 'tun' или 'vpn'
if nmcli -t -f TYPE con show --active | grep -qE "^(tun|vpn)$"; then
    echo "VPN"
else
    echo ""
fi