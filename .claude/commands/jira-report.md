---
description: Генерирует отчёт о прогрессе и отправляет в Jira. Использование: /jira-report ISSUE_KEY [--day | --N] [--auto] [--finish]
allowed-tools: Bash
---

Сгенерируй отчёт о прогрессе и отправь его в Jira.

## Шаг 1 — Разбери аргументы

Аргументы: `$ARGUMENTS`

Парсь так:
- Первый аргумент — ключ задачи Jira (обязательный, формат PROJECT-123, виден в URL: `/browse/PROJECT-123`)
- `--day` — взять все коммиты за сегодня (с midnight)
- `--N` где N — число — взять последние N коммитов (напр. `--2`, `--5`)
- `--auto` — отправить сразу без подтверждения
- `--finish` — после успешной отправки комментария переместить задачу в статус Done
- Если ни флага нет — по умолчанию `--1` (последний коммит)

Примеры:
- `/jira-report PROJECT-42` → последний коммит, показать превью, ждать подтверждения
- `/jira-report PROJECT-42 --day` → все коммиты за сегодня
- `/jira-report PROJECT-42 --3 --auto` → последние 3 коммита, отправить сразу
- `/jira-report PROJECT-42 --auto --finish` → отправить и сразу закрыть задачу

## Шаг 2 — Прочитай описание задачи из Jira

Сначала получи переменные (они могут быть заданы в fish, а не в текущем bash-окружении):
```bash
JIRA_URL=$(fish -c 'echo $JIRA_URL' 2>/dev/null || echo "$JIRA_URL")
JIRA_AUTH=$(fish -c 'echo $JIRA_AUTH' 2>/dev/null | tr -d '\n')
```

Затем сделай запрос:
```bash
curl -s "$JIRA_URL/rest/api/3/issue/$ISSUE_KEY?fields=summary,description" \
  -H "Authorization: Basic $JIRA_AUTH" \
  -H "Accept: application/json"
```

`$JIRA_AUTH` — base64 от `email:api_token` **без переносов строк**, кладётся в env заранее.
Из ответа извлеки `fields.summary` и `fields.description.content` (ADF-формат).
Используй как контекст — отчёт должен отражать прогресс именно по этой задаче.

## Шаг 3 — Получи данные коммитов

Если `--day`:
```bash
git log --since="midnight" --format="%H|%s|%ad" --date=format:"%d.%m.%y"
git diff $(git log --since="midnight" --format="%H" | tail -1)^ HEAD --stat
git diff $(git log --since="midnight" --format="%H" | tail -1)^ HEAD
```

Если `--N` (например --3):
```bash
git log -3 --format="%H|%s|%ad" --date=format:"%d.%m.%y"
git diff HEAD~3 HEAD --stat
git diff HEAD~3 HEAD
```

Если без флага (по умолчанию --1):
```bash
git log -1 --format="%H|%s|%ad" --date=format:"%d.%m.%y"
git diff HEAD~1 HEAD --stat
git diff HEAD~1 HEAD
```

Также:
```bash
git remote get-url origin
git rev-parse --short HEAD
git rev-parse HEAD
git branch --show-current
```

## Шаг 4 — Анализируй изменения

На основе описания задачи и diff определи:
- Что было сделано в контексте задачи (группируй по смыслу, не по файлам)
- Какой результат получился — что теперь работает / появилось
- Не углубляйся в детали реализации — уровень фич и архитектурных слоёв

## Шаг 5 — Составь структуру отчёта

Формат (для превью в чате):
```
Прогресс дня (ДД.ММ.ГГ)

1. Что сделано: <глагол + суть>
   - Подпункт
   - Подпункт

2. Что сделано: <глагол + суть>
   - Подпункт

Результат: <что теперь работает / появилось>

Ветка: BRANCH -> SHORT_HASH
https://github.com/OWNER/REPO/commit/FULL_HASH
```

Правила:
- Дата — из последнего коммита в выборке
- Пункты = логические группы изменений
- Каждый пункт начинается с глагола (Реализовал, Добавил, Разбил и т.д.)
- Ссылка на последний коммит в выборке

## Шаг 6 — Превью и отправка

Всегда сначала выведи превью:
```
📋 Превью отчёта для задачи ISSUE_KEY:
─────────────────────────────────────
<сгенерированный отчёт>
─────────────────────────────────────
```

Если передан флаг `--auto`:
- Сразу отправляй без вопросов, выведи "✅ Отправлено автоматически"

Если `--auto` НЕТ:
- После превью спроси: "Отправить отчёт? (да / нет / редактировать)"
- `да` — отправляй
- `нет` — отмена
- `редактировать` — попроси написать что изменить, исправь и покажи превью снова

Отправка комментария через Jira API в формате ADF (Atlassian Document Format).
Используй нативные ADF-ноды для форматирования — не plain text:
- Заголовок отчёта и заголовки пунктов — `paragraph` с маркой `strong`
- Подпункты — `bulletList` + `listItem`
- Ссылка на коммит — `text` с маркой `link`

Пример структуры ADF-тела:
```json
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [{"type": "text", "text": "Прогресс дня (17.03.26)", "marks": [{"type": "strong"}]}]
      },
      {
        "type": "paragraph",
        "content": [{"type": "text", "text": "1. Реализовал ...", "marks": [{"type": "strong"}]}]
      },
      {
        "type": "bulletList",
        "content": [
          {
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Подпункт"}]}]
          }
        ]
      },
      {
        "type": "paragraph",
        "content": [
          {"type": "text", "text": "Результат: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "описание результата"}
        ]
      },
      {
        "type": "paragraph",
        "content": [
          {"type": "text", "text": "Ветка: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "develop -> b143afd"}
        ]
      },
      {
        "type": "paragraph",
        "content": [
          {
            "type": "text",
            "text": "FULL_HASH",
            "marks": [{"type": "link", "attrs": {"href": "https://github.com/OWNER/REPO/commit/FULL_HASH"}}]
          }
        ]
      }
    ]
  }
}
```

Формируй ADF-тело программно через python3 — не через shell-интерполяцию строк:
```bash
python3 -c "
import json, subprocess

# Собери структуру ADF как Python-dict, затем сериализуй
body = { ... }  # полная ADF-структура
print(json.dumps(body))
" > /tmp/jira_body.json

curl -s -o /tmp/jira_response.json -w "%{http_code}" -X POST "$JIRA_URL/rest/api/3/issue/$ISSUE_KEY/comment" \
  -H "Authorization: Basic $JIRA_AUTH" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @/tmp/jira_body.json
```

После успешной отправки (HTTP 201) выведи ссылку: `$JIRA_URL/browse/$ISSUE_KEY`

## Шаг 7 — Перемести задачу в Done (только если передан `--finish`)

Если флаг `--finish` присутствует, после успешной отправки комментария:

**7.1 — Получи список доступных переходов:**
```bash
curl -s "$JIRA_URL/rest/api/3/issue/$ISSUE_KEY/transitions" \
  -H "Authorization: Basic $JIRA_AUTH" \
  -H "Accept: application/json"
```

Из ответа найди transition с именем `Done` (или `Готово` / `Closed` — ищи по полю `name`, регистр не важен).
Запомни его `id`.

**7.2 — Выполни переход:**
```bash
python3 -c "
import json
body = {'transition': {'id': 'TRANSITION_ID'}}
print(json.dumps(body))
" > /tmp/jira_transition.json

curl -s -o /tmp/jira_transition_response.json -w "%{http_code}" \
  -X POST "$JIRA_URL/rest/api/3/issue/$ISSUE_KEY/transitions" \
  -H "Authorization: Basic $JIRA_AUTH" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @/tmp/jira_transition.json
```

Успешный ответ — HTTP 204.
- Если 204 → выведи "✅ Задача $ISSUE_KEY перемещена в Done"
- Если ошибка или переход `Done` не найден среди доступных — выведи предупреждение с доступными статусами и не падай с ошибкой

## Env-переменные (должны быть заданы заранее)

**bash/zsh:**
```bash
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_AUTH="$(echo -n 'your@email.com:your_api_token' | base64 -w 0)"
```

**fish:**
```fish
set -Ux JIRA_URL "https://yourcompany.atlassian.net"
set -Ux JIRA_AUTH (echo -n 'your@email.com:your_api_token' | base64 | tr -d '\n')
```

> Важно: base64 на Linux без флага `-w 0` вставляет переносы строк каждые 76 символов — это ломает заголовок `Authorization`. Всегда strip newlines.

## Чтение переменных и вызов curl

Так как Claude Code работает в bash-окружении, переменные из fish нужно явно передавать:

```bash
JIRA_URL=$(fish -c 'echo $JIRA_URL')
JIRA_AUTH=$(fish -c 'echo $JIRA_AUTH' | tr -d '\n')
```

После этого используй `$JIRA_URL` и `$JIRA_AUTH` в curl-командах как обычно.
