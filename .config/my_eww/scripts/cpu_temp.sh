#!/bin/bash

temp=$(sensors -u k10temp-pci-00c3 | awk '/Tctl:/ {getline; printf "%d", $2}' 2>/dev/null)
if [ -z "$temp" ]; then temp=0; fi

if [ $temp -lt 40 ]; then
    icon="Холодно"; class="temp_cold"
elif [ $temp -lt 50 ]; then
    icon="Зашибись"; class="temp_normal"
elif [ $temp -lt 60 ]; then
    icon="Норм"; class="temp_warm"
elif [ $temp -lt 70 ]; then
    icon="Жарко"; class="temp_hot"
elif [ $temp -lt 80 ]; then
    icon="Вырубай!"; class="temp_very_hot"
else
    icon="-0_0-"; class="temp_critical"
fi

# Выводим два значения через пробел
echo "$icon $temp°C $class"
