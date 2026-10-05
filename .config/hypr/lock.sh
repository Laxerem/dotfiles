#!/bin/bash
# Блокировка экрана.
#
# Фон и переходы рисует lockfx.py — полноэкранный layer-shell слой:
#   блокировка    — рабочий стол приближается к центру и размывается,
#                   проявляются обои и частицы эффекта ($lock_fx из «Обоев»);
#   разблокировка — то же в обратную сторону.
# hyprlock (hyprlock-fx.conf) рисует поверх только часы и поле ввода: его фон
# прозрачный, а слой под ним виден благодаря misc:session_lock_xray, которая
# включена только на время блокировки. Если lockfx.py не запустился — обычный
# hyprlock.conf с обоями.
# Момент успешного ввода пароля берём из лога hyprlock (-v).
export XDG_RUNTIME_DIR=/run/user/$(id -u)  # обязательно для Wayland

# Один экземпляр: повторный Super+L, пока прошлый запуск ещё не завершился, игнорируем
exec 9>"$XDG_RUNTIME_DIR/hypr-lock.lock"
flock -n 9 || exit 0
pidof hyprlock >/dev/null && exit 0

HYPR=~/.config/hypr
conf_value() { sed -n "s/^\\\$$1 *= *//p" "$HYPR/lockscreen.conf" 2>/dev/null; }
LOCK_BG=$(conf_value lock_bg)
LOCK_FX=$(conf_value lock_fx)

fx_pid=
# fx_stop — запустить обратный переход (lockfx сам завершится); повторный вызов безвреден
fx_stop() { [ -n "$fx_pid" ] && kill -USR1 "$fx_pid" 2>/dev/null; }

cleanup() {
    [ -n "$fx_pid" ] && kill "$fx_pid" 2>/dev/null
    hyprctl keyword misc:session_lock_xray 0 >/dev/null
}
trap cleanup EXIT

hl_config=$HYPR/hyprlock.conf

coproc FX { exec python3 "$HYPR/lockfx.py" --effect "${LOCK_FX:-none}" --image "$LOCK_BG" 2>/dev/null; }
fx_pid=$FX_PID
# Ждём, пока переход к экрану блокировки закончится (~1.1 с); не дождались — блокируем без него
if read -t 4 -r reply <&"${FX[0]}" && [ "$reply" = ready ]; then
    hyprctl keyword misc:session_lock_xray 1 >/dev/null
    hl_config=$HYPR/hyprlock-fx.conf
else
    kill "$fx_pid" 2>/dev/null
    fx_pid=
fi

# stdbuf — чтобы строки лога приходили сразу, а не пачкой при выходе
stdbuf -oL hyprlock -v -c "$hl_config" 2>&1 | while IFS= read -r line; do
    case "$line" in
        *"auth: authenticated"* | *"Unlocking with a SIGUSR1"*)
            # Пароль принят: частицы гаснут вместе с часами. Во время своего растворения
            # hyprlock показывает снимок экрана без частиц — так они не «моргнут».
            [ -n "$fx_pid" ] && kill -USR2 "$fx_pid" 2>/dev/null
            ;;
        *"Unlocking session"*)
            # hyprlock растворил часы и отпустил экран — теперь обратный переход
            fx_stop
            ;;
    esac
done

# Ждём конца обратного перехода, потом cleanup выключит xray
fx_stop
[ -n "$fx_pid" ] && timeout 2 tail --pid="$fx_pid" -f /dev/null
fx_pid=
