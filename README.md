# dotfiles

Личные конфиги для Hyprland (Wayland, Arch Linux) и инструменты для [Claude Code](https://claude.ai/code).

## Содержимое

| Путь | Что это |
|---|---|
| `.config/hypr` | Hyprland: конфигурация WM, хоткеи |
| `.config/waybar` | Статус-бар |
| `.config/rofi` | Лаунчер приложений |
| `.config/eww`, `.config/my_eww` | Виджеты (eww) |
| `.config/dunst` | Уведомления |
| `.config/swaylock` | Экран блокировки |
| `.config/hyprdynamicmonitors` | Профили мониторов |
| `.config/kitty` | Терминал |
| `.config/nvim` | Neovim |
| `.config/cava` | Аудиовизуализатор |
| `.config/nwg-look`, `.config/Kvantum` | Темизация GTK/Qt |
| `.config/fontconfig`, `.config/xsettingsd`, `.config/htop` | Прочие системные настройки |
| `scripts/sync-dotfiles.sh` | Синхронизация `~/.config` ↔ репозиторий |
| `.claude/` | Команды и скиллы для Claude Code — см. [`.claude/README.md`](.claude/README.md) |

## Синхронизация конфигов

`scripts/sync-dotfiles.sh` копирует только директории из списка `TARGETS` внутри скрипта — остальное содержимое `~/.config` не трогается.

```bash
scripts/sync-dotfiles.sh push [--dry-run]   # ~/.config -> репозиторий
scripts/sync-dotfiles.sh pull [--dry-run]   # репозиторий -> ~/.config (разворачивание на новой машине)
```

Локальные Claude-настройки, бэкапы, обои и временные файлы синхронизацией игнорируются (см. `EXCLUDES` в скрипте).

## Claude Code

Репозиторий также содержит проектные команды и скиллы для Claude Code — интеграция с Redmine/Jira, код-ревью и другие рабочие процессы. Подробности и установка — в [`.claude/README.md`](.claude/README.md).

## Лицензия

MIT, см. [LICENSE](LICENSE).
