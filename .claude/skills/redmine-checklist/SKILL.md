---
name: redmine-checklist
description: Use when working with checklists in Redmine issues — reading, adding, updating, or deleting checklist items via the redmine_checklists plugin API
---

# Redmine Checklists — API skill

Этот файл описывает как читать и управлять чеклистами в Redmine через REST API.
Чеклисты доступны через плагин `redmine_checklists`.

Переменные окружения: `$REDMINE_URL`, `$REDMINE_API_KEY`

---

## Читать чеклист задачи

```bash
curl -s "$REDMINE_URL/issues/{ISSUE_ID}/checklists.json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

**Ответ:**
```json
{
  "checklists": [
    {
      "id": 861,
      "issue_id": 8887,
      "subject": "Страница обзора",
      "is_done": true,
      "position": 0,
      "is_section": false,
      "created_at": "2026-04-17T20:07:50Z",
      "updated_at": "2026-04-17T21:17:55Z"
    }
  ],
  "total_count": 1
}
```

Поля:
- `id` — ID пункта (нужен для обновления/удаления)
- `subject` — текст пункта
- `is_done` — отмечен ли (`true` / `false`)
- `position` — порядок (0-based)
- `is_section` — является ли разделителем-заголовком

---

## Добавить пункт

```bash
curl -s -X POST "$REDMINE_URL/issues/{ISSUE_ID}/checklists.json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"checklist": {"subject": "Текст пункта", "is_done": false}}'
```

**Ответ:** объект созданного пункта с присвоенным `id`.

Добавить несколько — вызывать последовательно по одному запросу на пункт.

---

## Обновить пункт (отметить/снять/переименовать)

```bash
curl -s -X PUT "$REDMINE_URL/issues/{ISSUE_ID}/checklists/{CHECKLIST_ID}.json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"checklist": {"is_done": true}}'
```

Можно обновить одно или несколько полей: `subject`, `is_done`, `position`.
Ответ: HTTP 200 с обновлённым объектом.

---

## Удалить пункт

```bash
curl -s -X DELETE "$REDMINE_URL/issues/{ISSUE_ID}/checklists/{CHECKLIST_ID}.json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

Ответ: HTTP 200. Если нет прав — вернёт 403.

---

## Python-шаблон для батчевых операций

```python
import urllib.request, json, os

URL = os.environ['REDMINE_URL']
KEY = os.environ['REDMINE_API_KEY']
HEADERS = {"X-Redmine-API-Key": KEY, "Content-Type": "application/json"}

def checklist_list(issue_id):
    req = urllib.request.Request(f"{URL}/issues/{issue_id}/checklists.json", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["checklists"]

def checklist_add(issue_id, subject, is_done=False):
    data = json.dumps({"checklist": {"subject": subject, "is_done": is_done}}).encode()
    req = urllib.request.Request(f"{URL}/issues/{issue_id}/checklists.json", data=data, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["checklist"]

def checklist_update(issue_id, checklist_id, **fields):
    data = json.dumps({"checklist": fields}).encode()
    req = urllib.request.Request(f"{URL}/issues/{issue_id}/checklists/{checklist_id}.json", data=data, headers=HEADERS, method="PUT")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def checklist_delete(issue_id, checklist_id):
    req = urllib.request.Request(f"{URL}/issues/{issue_id}/checklists/{checklist_id}.json", headers=HEADERS, method="DELETE")
    with urllib.request.urlopen(req) as r:
        return r.status
```

---

## Типичные сценарии

**Показать чеклист задачи в читаемом виде:**
```python
items = checklist_list(8887)
for item in items:
    mark = "✅" if item["is_done"] else "⬜"
    print(f"{mark} [{item['id']}] {item['subject']}")
```

**Добавить несколько пунктов, не трогая существующие:**
```python
new_items = ["UI создания модели", "UI редактирования модели"]
for subject in new_items:
    result = checklist_add(8887, subject)
    print(f"  + добавлен id={result['id']}: {subject}")
```

**Отметить пункт как выполненный по его id:**
```python
checklist_update(8887, 861, is_done=True)
```

---

## Важно

- Эндпоинт `GET /checklists.json?issue_id=X` — не существует, возвращает 404. Только `GET /issues/{id}/checklists.json`
- `include=checklists` в запросе задачи не работает — чеклисты не возвращаются через стандартный API задачи
- Порядок пунктов при добавлении — новые добавляются в конец списка
