#!/usr/bin/env bash
# Напоминание о замере состояния (Настроение/Энергия/Прогресс) в Obsidian.
# Уведомление само закрывается через минуту, если его игнорировать.
# Клик по нему — единственный способ открыть Obsidian, никакого авто-открытия.
set -euo pipefail

URI="obsidian://quickadd?vault=Obsidian%20Vault&choice=%D0%97%D0%B0%D0%BC%D0%B5%D1%80%20%D1%81%D0%BE%D1%81%D1%82%D0%BE%D1%8F%D0%BD%D0%B8%D1%8F"
OBSIDIAN_CLASS="md.obsidian.Obsidian"

action=$(dunstify -w -A "default,Открыть" -u normal -a "QuickAdd" -t 60000 \
  "Замер состояния" "Отметь настроение / энергию / прогресс") || true

if [ "$action" = "default" ]; then
    # Если Obsidian уже открыт — переключаемся на его рабочий стол/окно.
    # Если не открыт — просто ничего не найдётся, идём дальше без ошибки.
    hyprctl dispatch focuswindow "class:^(${OBSIDIAN_CLASS})$" >/dev/null 2>&1 || true
    # xdg-open блокируется до завершения запущенного процесса при холодном
    # старте Obsidian — запускаем в фоне, чтобы не подвесить сам скрипт.
    setsid xdg-open "$URI" >/dev/null 2>&1 &
    disown
fi
