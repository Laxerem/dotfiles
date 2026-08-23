# Claude Code tooling

Кастомные команды и скиллы для [Claude Code](https://claude.ai/code), используемые в связке с Redmine/Jira и для код-ревью.

## Установка

Команды и скиллы работают из этого репозитория как project-level (`.claude/`). Для глобальной установки:

```bash
cp .claude/commands/*.md ~/.claude/commands/
cp -r .claude/skills/* ~/.claude/skills/
```

## Команды

| Команда | Назначение |
|---|---|
| [`/pm`](commands/pm.md) | PM-агент для Redmine: обзор проектов, декомпозиция задач из файла |
| [`/report`](commands/report.md) | Отчёт о прогрессе в задачу Redmine на основе git-коммитов |
| [`/jira-report`](commands/jira-report.md) | То же самое для Jira (ADF-формат) |
| [`/review`](commands/review.md) | Code review коммитов с опциональной сверкой против задачи Redmine |

### `/pm` — PM-агент для Redmine

```
/pm                                          # Обзор всех проектов, интерактивный режим
/pm --project "Name"                         # Сводка по проекту (статусы, приоритеты, просрочки)
/pm --tasks "tasks.md"                       # Декомпозиция задач из файла → Redmine
/pm --project "Name" --tasks "tasks.md"      # Сводка + декомпозиция
```

В режиме `--tasks`: читает файл → предлагает структуру декомпозиции → показывает пример одной задачи и ждёт подтверждения → создаёт `redmine-tasks-plan.md` → одним Python-скриптом создаёт все задачи в Redmine и добавляет связи → обновляет заголовки в `redmine-tasks-plan.md` ссылками на созданные задачи.

**Env:** `REDMINE_URL`, `REDMINE_API_KEY`

### `/report` — отчёт в Redmine

```
/report 42              # Последний коммит, превью, ждёт подтверждения
/report 42 --day        # Все коммиты за сегодня
/report 42 --3          # Последние 3 коммита
/report 42 --day --auto # Отправить сразу без подтверждения
```

Читает описание задачи из Redmine → анализирует diff → формирует отчёт в Textile → показывает превью → отправляет PUT-запросом.

**Env:** `REDMINE_URL`, `REDMINE_API_KEY`

### `/jira-report` — отчёт в Jira

```
/jira-report PROJECT-42              # Последний коммит, превью, ждёт подтверждения
/jira-report PROJECT-42 --day        # Все коммиты за сегодня
/jira-report PROJECT-42 --3 --auto   # Последние 3 коммита, отправить сразу
/jira-report PROJECT-42 --auto --finish  # Отправить и перевести задачу в Done
```

Аналог `/report` для Jira. Комментарий отправляется в формате ADF. С `--finish` задача переводится в Done.

**Env:** `JIRA_URL`, `JIRA_AUTH` (base64 от `email:api_token`)

### `/review` — code review

```
/review                     # Последний коммит
/review --day               # Все коммиты за сегодня
/review --n 3               # Последние 3 коммита
/review --author "Name"     # Фильтр по автору
/review --task 42           # Сравнить с требованиями задачи Redmine + предложить отправить отчёт
```

Собирает git diff → формирует отчёт (Markdown для чата, Textile для Redmine) с разделами: сводка, что сделано хорошо, замечания, архитектура, итоговый вердикт. С `--task` сравнивает diff с требованиями задачи и предлагает отправить отчёт в Redmine.

**Env (только при `--task`):** `REDMINE_URL`, `REDMINE_API_KEY`

## Скиллы

| Скилл | Назначение |
|---|---|
| [`redmine-checklist`](skills/redmine-checklist/SKILL.md) | Работа с чек-листами в задачах Redmine (плагин `redmine_checklists`) |
| [`redmine-sprints`](skills/redmine-sprints/SKILL.md) | Чтение спринтов через плагин Easy Agile |
| [`prompt-engineering`](skills/prompt-engineering/SKILL.md) | Проектирование и диагностика промптов для LLM |
| [`explanation-of-the-topic`](skills/explanation-of-the-topic/SKILL.md) | Объяснение концепций в роли ментора для изучающего C#/.NET backend |
| [`writing-styles`](skills/writing-styles/authorial-voice.md) | Авторский стиль для технических текстов на русском (changelog, статусы, сообщения) |

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
