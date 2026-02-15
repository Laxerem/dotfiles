#!/bin/bash

WALL_DIR="$HOME/.config/hypr/wallpapers"

# 1. Выбираем случайное фото
WALLPAPER=$(find "$WALL_DIR" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) | shuf -n 1)

# 2. Проверяем, запущен ли hyprpaper. Если нет — запускаем.
if ! pgrep -x "hyprpaper" > /dev/null; then
    hyprpaper &
    sleep 0.4 # Даем долю секунды на инициализацию
fi

# 3. Принудительно выгружаем всё старое, чтобы не копилось в RAM
hyprctl hyprpaper unload all

# 4. Загружаем и устанавливаем новое
hyprctl hyprpaper preload "$WALLPAPER"
hyprctl hyprpaper wallpaper ",$WALLPAPER"
