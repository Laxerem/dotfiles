#!/bin/bash
# fast polling текущей раскладки
while true; do
    layout=$(setxkbmap -query | awk '/layout/ {print $2}')
    case $layout in
        us) echo "🇺🇸" ;;
        ru) echo "🇷🇺" ;;
        *) echo "$layout" ;;
    esac
    sleep 0.2
done
