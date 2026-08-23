#!/bin/bash

# Получаем загрузку CPU
usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
usage_int=$(printf "%.0f" $usage)

# Выбираем иконку и цвет в зависимости от нагрузки
if [ $usage_int -lt 30 ]; then
    icon=""
    color="#a3be8c"
elif [ $usage_int -lt 60 ]; then
    icon=""
    color="#ebcb8b"
elif [ $usage_int -lt 80 ]; then
    icon=""
    color="#d08770"
else
    icon=""
    color="#bf616a"
fi

echo "<span color='$color'>$icon $usage_int%</span>"
