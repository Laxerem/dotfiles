# dotfiles

Кастомные команды для [Claude Code](https://claude.ai/code).

Команды хранятся в `.claude/commands/`. Для глобальной установки:
```bash
cp .claude/commands/*.md ~/.claude/commands/
```

---

## `/pm` — PM-агент для Redmine

Управление задачами в Redmine: просмотр проектов, создание и обновление задач, декомпозиция из файла.

```
/pm                                          # Обзор всех проектов, интерактивный режим
/pm --project "Name"                         # Сводка по проекту (статусы, приоритеты, просрочки)
/pm --tasks "tasks.md"                       # Декомпозиция задач из файла → Redmine
/pm --project "Name" --tasks "tasks.md"      # Сводка + декомпозиция
```

**Как работает в режиме `--tasks`:**
1. Читает файл, предлагает структуру декомпозиции
2. Показывает пример одной задачи — ждёт подтверждения
3. Создаёт `redmine-tasks-plan.md` с детальным описанием задач
4. Одним Python-скриптом создаёт все задачи в Redmine и добавляет связи
5. Обновляет заголовки в `redmine-tasks-plan.md`, добавляя ссылки на созданные задачи

**Env:** `REDMINE_URL`, `REDMINE_API_KEY`

---

## `/report` — Отчёт о прогрессе в Redmine

Генерирует отчёт на основе git-коммитов и отправляет его заметкой к задаче Redmine.

```
/report 42              # Последний коммит, превью, ждёт подтверждения
/report 42 --day        # Все коммиты за сегодня
/report 42 --3          # Последние 3 коммита
/report 42 --day --auto # Отправить сразу без подтверждения
```

**Как работает:** читает описание задачи из Redmine → анализирует diff → формирует отчёт в Textile → показывает превью → отправляет PUT-запросом.

**Env:** `REDMINE_URL`, `REDMINE_API_KEY`

---

## `/jira-report` — Отчёт о прогрессе в Jira

Аналог `/report`, но для Jira. Отправляет комментарий в формате ADF (Atlassian Document Format).

```
/jira-report PROJECT-42              # Последний коммит, превью, ждёт подтверждения
/jira-report PROJECT-42 --day        # Все коммиты за сегодня
/jira-report PROJECT-42 --3 --auto   # Последние 3 коммита, отправить сразу
/jira-report PROJECT-42 --auto --finish  # Отправить и перевести задачу в Done
```

**Как работает:** читает описание задачи из Jira → анализирует diff → формирует отчёт → показывает превью → отправляет через Jira API. С `--finish` выполняет переход задачи в Done.

**Env:** `JIRA_URL`, `JIRA_AUTH` (base64 от `email:api_token`)

---

## `/review` — Code Review

Анализирует коммиты и выдаёт code review с оценкой по критериям. Поддерживает интеграцию с Redmine.

```
/review                     # Последний коммит
/review --day               # Все коммиты за сегодня
/review --n 3               # Последние 3 коммита
/review --author "Name"     # Фильтр по автору
/review --task 42           # Сравнить с требованиями задачи Redmine + предложить отправить отчёт
```

**Как работает:** собирает git diff → анализирует изменения → формирует отчёт (Markdown для чата + Textile для Redmine) с разделами: сводка, что сделано хорошо, замечания, архитектура, итоговый вердикт. С `--task` сравнивает diff с требованиями задачи и предлагает отправить отчёт в Redmine.

**Env (только при `--task`):** `REDMINE_URL`, `REDMINE_API_KEY`

---

## Переменные окружения

**fish** (`~/.config/fish/config.fish`):
```fish
set -Ux REDMINE_URL "https://pm.example.com"
set -Ux REDMINE_API_KEY "your_api_key"
set -Ux JIRA_URL "https://yourcompany.atlassian.net"
set -Ux JIRA_AUTH (echo -n 'your@email.com:your_api_token' | base64 | tr -d '\n')
```

**bash/zsh:**
```bash
export REDMINE_URL="https://pm.example.com"
export REDMINE_API_KEY="your_api_key"
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_AUTH="$(echo -n 'your@email.com:your_api_token' | base64 -w 0)"
```
