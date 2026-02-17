#!/bin/bash

# Закрывает popup с задержкой, если курсор не вернулся.
# Использование: close_popup_delayed.sh <имя_окна> <hover_переменная>

EWW="eww -c /home/laxerem/.config/my_eww"
POPUP="$1"
HOVER_VAR="$2"

if [ "$($EWW get "$HOVER_VAR")" = "false" ]; then
    $EWW close "$POPUP" 2>/dev/null
fi
