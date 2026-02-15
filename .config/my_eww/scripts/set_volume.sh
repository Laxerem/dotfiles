#!/bin/bash

# Устанавливаем громкость
pamixer --set-volume "$1"

# Путь к звуковому файлу (можно настроить)
SOUND_FILE="/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"

# Проигрываем звук (используем paplay для PulseAudio/PipeWire)
if [ -f "$SOUND_FILE" ]; then
    paplay "$SOUND_FILE" &
fi
