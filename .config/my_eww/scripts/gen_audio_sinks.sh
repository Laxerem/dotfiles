#!/bin/bash

# Получаем устройство по умолчанию
default_sink=$(pactl get-default-sink)

# Начинаем вывод с открывающего box
echo -n "(box :orientation \"vertical\" :spacing 5 "

# Генерируем виджеты для каждого устройства
pactl list sinks | awk -v def_sink="$default_sink" '
/^Sink #/ {
    sink_id = $2
    gsub(/#/, "", sink_id)
}
/Name:/ {
    name = $2
}
/Description:/ {
    desc = $0
    sub(/.*Description: /, "", desc)
    is_default = (name == def_sink)

    # Сокращаем длинные названия
    if (length(desc) > 35) {
        desc = substr(desc, 1, 32) "..."
    }

    # Генерируем виджет кнопки
    class_name = is_default ? "audio-sink-active" : "audio-sink"
    icon = is_default ? "󰄲" : "󰋋"

    printf "(button :class \"%s\" :onclick \"pactl set-default-sink %s\" (box :orientation \"horizontal\" :space-evenly false (box :hexpand false (label :class \"audio-sink-icon\" :text \"%s\")) (box :hexpand false (label :class \"audio-sink-text\" :text \"%s\"))))", class_name, name, icon, desc
}
'

# Закрываем box
echo ")"
