# Test results

Дата фиксации результатов: 2026-05-02.

## Проверки

| Команда | Результат |
| --- | --- |
| `docker compose up --build` | Успешно |
| `docker compose exec web python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `docker compose exec web python manage.py migrate` | `No migrations to apply` |
| `docker compose exec web pytest` | `46 passed`, coverage `100.00%` |
| `schemathesis run http://localhost:8000/api/schema/` с JWT | `48 passed`, `not_a_server_error 3909/3909 passed` |
| `python manage.py spectacular --file schema.yml` | Успешно |

## Примечание

Предупреждение Schemathesis/jsonschema относится к сторонней библиотеке и не ломает тесты. Проверки проходят успешно, а API-инвариант `not_a_server_error` выполнен для всех `3909/3909` сгенерированных проверок.
