#!/bin/bash

# Получаем температуру
temp=$(sensors -u k10temp-pci-00c3 | awk '/Tctl:/ {getline; printf "%d", $2}' 2>/dev/null)

# Если не удалось получить температуру, используем значение по умолчанию
if [ -z "$temp" ]; then
    temp=0
fi

# Выбираем иконку в зависимости от температуры
if [ $temp -lt 40 ]; then
    icon="Холодно"
    class="temp_cold"
elif [ $temp -lt 50 ]; then
    icon="Зашибись"
    class="temp_normal"
elif [ $temp -lt 60 ]; then
    icon="It's ok"
    class="temp_warm"
elif [ $temp -lt 70 ]; then
    icon="Жарко"
    class="temp_hot"
elif [ $temp -lt 80 ]; then
    icon="Вырубай шарманку!"
    class="temp_very_hot"
else
    icon="Я щас сдохну"
    class="temp_critical"
fi

# Выводим в JSON формате
echo "{\"text\": \"$icon $temp°C\", \"tooltip\": \"CPU Temperature: $temp°C\", \"class\": \"$class\"}"
