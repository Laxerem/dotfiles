#!/bin/bash

# Открывает popup, закрывая все остальные.
# Использование: open_popup.sh <имя_окна>

EWW="eww -c /home/laxerem/.config/my_eww"
WINDOW="$1"
ALL_POPUPS="volume-popup wifi-popup"

for p in $ALL_POPUPS; do
    if [ "$p" != "$WINDOW" ]; then
        $EWW close "$p" 2>/dev/null
    fi
done

$EWW open "$WINDOW" 2>/dev/null
