#!/bin/bash
# Запуск терминала по Super+Enter.
# Если на текущем рабочем столе терминалов ещё нет — открывается kitty с классом
# kitty-first, на который в hyprland.conf висит правило (floating, по центру).
# Если терминал уже есть — floating-терминал переводится в tiled, и открывается
# обычный kitty (тоже tiled).

ws=$(hyprctl activeworkspace -j | jq -r '.id')
terms=$(hyprctl clients -j | jq -c --argjson ws "$ws" \
    '[.[] | select(.workspace.id == $ws and (.class == "kitty" or .class == "kitty-first"))]')

if [[ $(jq 'length' <<<"$terms") -eq 0 ]]; then
    exec kitty --class kitty-first
fi

# Floating-терминалы на этом рабочем столе переводим в tiled, чтобы новое окно легло рядом
while read -r addr; do
    hyprctl dispatch settiled "address:$addr" >/dev/null
done < <(jq -r '.[] | select(.floating) | .address' <<<"$terms")

exec kitty
