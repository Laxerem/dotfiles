#!/bin/bash

# Скрипт генерирует yuck-код для списка доступных Wi-Fi сетей

# Получаем текущую подключенную сеть
current_ssid=$(iwgetid -r)

# Получаем список сохраненных подключений
saved_connections=$(nmcli -t -f NAME connection show)

# Начинаем вывод с открывающего box
echo -n "(box :orientation \"vertical\" :spacing 3 "

# Сканируем доступные сети, убираем дубликаты и добавляем метку сохраненности
nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list | \
    awk -F':' '!seen[$2]++ {print}' | \
    while IFS=':' read -r in_use ssid signal security; do
        # Пропускаем пустые SSID
        [ -z "$ssid" ] && continue

        # Проверяем, сохранена ли сеть
        if echo "$saved_connections" | grep -qxF "$ssid"; then
            is_saved="1"
        else
            is_saved="0"
        fi

        # Выводим в формате: is_saved:signal:in_use:ssid:security
        # is_saved=1 для сохраненных (они будут первыми при сортировке по убыванию)
        echo "$is_saved:$signal:$in_use:$ssid:$security"
    done | \
    sort -t':' -k1,1rn -k2,2rn | \
    while IFS=':' read -r is_saved signal in_use ssid security; do
        # Определяем иконку по уровню сигнала
        if [ "$signal" -ge 75 ]; then
            signal_icon="󰤨"
        elif [ "$signal" -ge 50 ]; then
            signal_icon="󰤥"
        elif [ "$signal" -ge 25 ]; then
            signal_icon="󰤢"
        else
            signal_icon="󰤟"
        fi

        # Для сохраненных сетей - зеленая иконка, без замка
        # Для несохраненных - обычная иконка, с замком если защищена
        if [ "$is_saved" = "1" ]; then
            signal_class="wifi-network-signal-saved"
            lock_icon=""
        else
            signal_class="wifi-network-signal"
            if echo "$security" | grep -q "WPA"; then
                lock_icon="󰌾"
            else
                lock_icon=""
            fi
        fi

        # Определяем активна ли эта сеть
        class_name="wifi-network"
        if [ "$ssid" = "$current_ssid" ]; then
            class_name="wifi-network-active"
        fi

        # Экранируем специальные символы в SSID
        ssid_escaped=$(echo "$ssid" | sed 's/"/\\"/g' | sed "s/'/\\\\'/g")

        # Формируем команду подключения
        if [ "$is_saved" = "1" ]; then
            # Для сохраненных сетей - прямое подключение
            connect_cmd="~/.config/my_eww/scripts/connect_wifi.sh '$ssid_escaped' 'saved'"
        else
            # Для несохраненных - показать поле ввода пароля
            connect_cmd="eww -c /home/laxerem/.config/my_eww/ update wifi_connect_ssid='$ssid_escaped' && eww -c /home/laxerem/.config/my_eww/ update wifi_show_password=true"
        fi

        # Генерируем виджет кнопки для сети
        printf "(button :class \"%s\" :onclick \"%s\" (box :orientation \"horizontal\" :space-evenly false :spacing 5 (box :hexpand false (label :class \"%s\" :text \"%s\")) (box :hexpand false (label :class \"wifi-network-lock\" :text \"%s\")) (box :hexpand true (label :class \"wifi-network-name\" :text \"%s\" :xalign 0 :limit-width 20 :truncate true)) (box :hexpand false (label :class \"wifi-network-strength\" :text \"%s%%\"))))" \
            "$class_name" "$connect_cmd" "$signal_class" "$signal_icon" "$lock_icon" "$ssid_escaped" "$signal"
    done

# Добавляем кнопку для повторного сканирования
echo -n "(box :vexpand false (button :class \"wifi-rescan-btn\" :onclick \"nmcli device wifi rescan && sleep 1\" (label :text \"󰑓 Обновить\")))"

# Закрываем box
echo ")"
