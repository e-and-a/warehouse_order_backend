# Fuzzing report

## Цель

Schemathesis используется для фаззинг-тестирования REST API по OpenAPI-схеме. Основная цель: убедиться, что API возвращает контролируемые 4xx-ответы на некорректные входные данные, а не 500.

## Проверяемые endpoints

- Authentication: `/api/auth/token/`, `/api/auth/token/refresh/`
- Users: `/api/users/`, `/api/users/me/`
- Catalog: `/api/categories/`, `/api/products/`
- Warehouse: `/api/warehouses/`, `/api/stock/`
- Orders: `/api/customers/`, `/api/orders/`, `/api/orders/{id}/change-status/`
- Audit: `/api/audit-log/`

## Типы некорректных данных

- Пустые обязательные поля.
- Некорректные enum значения для ролей и статусов.
- Отрицательные `quantity`, `reserved_quantity` и `price`.
- `reserved_quantity > quantity`.
- Несуществующие foreign keys.
- Неверный формат email.
- Запросы без JWT или с ролью без нужных прав.

## Ожидаемые результаты

- Ошибки валидации возвращают `400`.
- Отсутствие JWT возвращает `401`.
- Недостаточная роль возвращает `403`.
- Некорректные status transitions возвращают `400`.
- Сервер не должен возвращать `500` для пользовательских ошибок ввода.

## Пример запуска

```bash
schemathesis run http://localhost:8000/api/schema/
```

Для authenticated endpoints передайте JWT:

```bash
schemathesis run http://localhost:8000/api/schema/ \
  --header "Authorization: Bearer <access_token>"
```
