#!/bin/bash
# Выбор окна из списка hyprctl clients и настройка его режима (floating/tiled)
# и размера по умолчанию. Настройка применяется сразу и сохраняется в
# ~/.config/hypr/window-rules-custom.conf, поэтому переживает перезапуск Hyprland.

ROFI_THEME="$HOME/.config/rofi/conf.rasi"
RULES_FILE="$HOME/.config/hypr/window-rules-custom.conf"
HYPR_CONF="$HOME/.config/hypr/hyprland.conf"

notify() {
    command -v notify-send >/dev/null 2>&1 && notify-send -a "Window Default" "$1" "$2"
}

die() {
    notify "Window Default" "$1"
    echo "$1" >&2
    exit 1
}

for bin in hyprctl jq rofi; do
    command -v "$bin" >/dev/null 2>&1 || die "Не найден '$bin', установи его для работы скрипта"
done

rofi_pick() {
    # $1 - подпись, остальное игнорируется; список приходит через stdin
    rofi -dmenu -i -p "$1" -theme "$ROFI_THEME"
}

# --- убеждаемся, что файл с правилами существует и подключён в hyprland.conf ---

mkdir -p "$(dirname "$RULES_FILE")"

if [[ ! -f "$RULES_FILE" ]]; then
    cat > "$RULES_FILE" <<'EOF'
# Правила окон, управляемые window-default.sh.
# Каждая запись привязана к классу окна и перезаписывается при повторной настройке того же класса.
EOF
fi

if ! grep -qF "source = $RULES_FILE" "$HYPR_CONF" 2>/dev/null; then
    first_windowrule_line=$(grep -n "^windowrule" "$HYPR_CONF" | head -1 | cut -d: -f1)
    if [[ -n "$first_windowrule_line" ]]; then
        tmp_insert=$(mktemp)
        cat > "$tmp_insert" <<EOF

# Правило подключено скриптом window-default.sh (не редактируй эту строку вручную)
source = ${RULES_FILE}

EOF
        sed -i "$((first_windowrule_line - 1))r ${tmp_insert}" "$HYPR_CONF"
        rm -f "$tmp_insert"
    else
        printf '\nsource = %s\n' "$RULES_FILE" >> "$HYPR_CONF"
    fi
fi

# --- получаем список окон ---

mapfile -t CLIENTS < <(hyprctl clients -j | jq -c '.[] | select(.mapped == true)')

if [[ ${#CLIENTS[@]} -eq 0 ]]; then
    die "Нет открытых окон"
fi

LABELS=()
for entry in "${CLIENTS[@]}"; do
    ws=$(jq -r '.workspace.name' <<<"$entry")
    class=$(jq -r '.class' <<<"$entry")
    title=$(jq -r '.title' <<<"$entry" | cut -c1-60)
    floating=$(jq -r '.floating' <<<"$entry")
    mode="tiled"
    [[ "$floating" == "true" ]] && mode="floating"
    LABELS+=("[ws $ws | $mode] $class — $title")
done

selected_index=$(printf '%s\n' "${LABELS[@]}" | rofi -dmenu -i -p "Выбери окно" -format i -theme "$ROFI_THEME")
[[ -z "$selected_index" ]] && exit 0

chosen="${CLIENTS[$selected_index]}"
ADDR=$(jq -r '.address' <<<"$chosen")
CLASS=$(jq -r '.class' <<<"$chosen")

[[ -z "$CLASS" || "$CLASS" == "null" ]] && die "У окна пустой class, настроить правило по классу нельзя"

# --- режим: floating или tiled ---

mode=$(printf 'Floating\nTiled\n' | rofi_pick "Режим окна")
[[ -z "$mode" ]] && exit 0

# --- размер (только для floating) ---

size=""
if [[ "$mode" == "Floating" ]]; then
    size_choice=$(printf '800x450\n1000x600\n1280x720\n1300x700\n1600x900\n1920x1080\nСвой размер\nБез изменения размера\n' | rofi_pick "Размер окна")
    [[ -z "$size_choice" ]] && exit 0

    if [[ "$size_choice" == "Свой размер" ]]; then
        size_choice=$(rofi -dmenu -i -p "Введи ШxВ (например 900x600)" -theme "$ROFI_THEME")
        [[ -z "$size_choice" ]] && exit 0
    fi

    if [[ "$size_choice" != "Без изменения размера" ]]; then
        if [[ "$size_choice" =~ ^([0-9]+)x([0-9]+)$ ]]; then
            size="$size_choice"
        else
            die "Неверный формат размера: '$size_choice', ожидается ШxВ"
        fi
    fi
fi

# --- применяем сразу к текущему окну ---

hyprctl dispatch focuswindow "address:$ADDR" >/dev/null

if [[ "$mode" == "Floating" ]]; then
    hyprctl dispatch setfloating >/dev/null
else
    hyprctl dispatch settiled >/dev/null
fi

if [[ -n "$size" ]]; then
    w="${size%x*}"
    h="${size#*x}"
    hyprctl dispatch resizeactive exact "$w" "$h" >/dev/null
fi

# --- сохраняем правило, чтобы оно применялось и после перезапуска/перезагрузки ---

ESCAPED_CLASS=$(printf '%s' "$CLASS" | sed 's/[.[\*^$()+?{}|\\]/\\&/g')
RULE_MATCH="match:class ^(${ESCAPED_CLASS})\$,"

if [[ "$mode" == "Floating" ]]; then
    if [[ -n "$size" ]]; then
        NEW_RULE="windowrule = ${RULE_MATCH} float yes, size ${w} ${h}"
    else
        NEW_RULE="windowrule = ${RULE_MATCH} float yes"
    fi
else
    NEW_RULE="windowrule = ${RULE_MATCH} tile yes"
fi

TMP_FILE=$(mktemp)
grep -vF "$RULE_MATCH" "$RULES_FILE" > "$TMP_FILE"
printf '%s\n' "$NEW_RULE" >> "$TMP_FILE"
mv "$TMP_FILE" "$RULES_FILE"

notify "Window Default" "$CLASS -> $mode${size:+, $size}. Правило сохранено."
