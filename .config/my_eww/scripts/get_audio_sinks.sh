#!/bin/bash

# Получаем устройство по умолчанию
default_sink=$(pactl get-default-sink)

# Получаем список всех устройств
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
    is_default = (name == def_sink) ? "true" : "false"
    # Сокращаем длинные названия
    if (length(desc) > 30) {
        desc = substr(desc, 1, 27) "..."
    }
    printf "{\"name\":\"%s\",\"desc\":\"%s\",\"default\":\"%s\"}\n", name, desc, is_default
}
'
