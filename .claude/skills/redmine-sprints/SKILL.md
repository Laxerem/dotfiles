---
name: redmine-sprints
description: Use when working with sprints in Redmine — reading sprints via the Easy Agile plugin API
---

# Redmine Sprints — API skill

Спринты в Redmine реализованы через плагин **Easy Agile** (модули `agile`, `agile_backlog`).
Стандартный Redmine API (`/projects/ID/versions.json`) спринты не возвращает.

Переменные окружения: `$REDMINE_URL`, `$REDMINE_API_KEY`

---

## Получить спринты проекта

```bash
curl -s "$REDMINE_URL/projects/{PROJECT_ID}/agile_sprints.json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

`PROJECT_ID` — числовой ID или идентификатор (`identifier`) проекта.

**Ответ:**
```json
{
  "project_id": 490,
  "project_name": "Связка нейросетей",
  "sprints": [
    {
      "id": 105,
      "name": "Осмысление проблемы",
      "description": "Изучить описание задачи, сформулировать вопросы",
      "start_date": "2025-10-23",
      "end_date": "2025-10-28"
    },
    {
      "id": 106,
      "name": "Подготовка ресурсов",
      "description": "Разработка архитектуры, подбор команды, обсуждение API",
      "start_date": "2025-10-28",
      "end_date": "2025-11-01"
    }
  ]
}
```

Поля спринта:
- `id` — ID спринта (нужен для последующих операций)
- `name` — название
- `description` — описание
- `start_date` / `end_date` — даты в формате `YYYY-MM-DD`

---

## Python-шаблон

```python
import urllib.request, json, os

URL = os.environ['REDMINE_URL']
KEY = os.environ['REDMINE_API_KEY']
HEADERS = {"X-Redmine-API-Key": KEY}

def sprints_list(project_id):
    req = urllib.request.Request(
        f"{URL}/projects/{project_id}/agile_sprints.json",
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["sprints"]
```

---

## Типичный сценарий

**Показать спринты проекта в читаемом виде:**
```python
sprints = sprints_list(490)
for s in sprints:
    print(f"[{s['id']}] {s['name']} | {s['start_date']} — {s['end_date']}")
    if s.get('description'):
        print(f"     {s['description']}")
```

---

## Важно

- Эндпоинт `/projects/ID/versions.json` — спринты **не возвращает**, там всегда пустой массив
- Эндпоинт `/agile_sprints.json?project_id=ID` (без `projects/`) — возвращает 404
- Эндпоинт `/projects/ID/sprints.json` — возвращает 404
- Работает только `/projects/{ID}/agile_sprints.json`
