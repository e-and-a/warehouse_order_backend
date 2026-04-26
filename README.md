# warehouse_order_backend

Клиент-серверное приложение на Django и Django REST Framework для управления каталогом, складами, остатками, клиентами и заказами.

## Стек

- Python 3.12
- Django, Django REST Framework
- PostgreSQL
- djangorestframework-simplejwt
- drf-spectacular
- pytest, pytest-django
- Docker, Docker Compose
- django-environ
- gunicorn, whitenoise

## Структура

```text
config/                 Django settings, urls, template views
apps/users/             кастомный User, роли, permissions
apps/catalog/           категории и товары
apps/warehouse/         склады, остатки, складской service layer
apps/orders/            клиенты, заказы, order service layer, seed_data
apps/audit/             audit log
templates/              Django Templates клиент
static/                 CSS
tests/                  pytest tests
docs/                   дополнительная документация
```

## Роли

- `ADMIN`: полный доступ, управление пользователями и audit log.
- `MANAGER`: управление товарами, складами, остатками, клиентами и заказами.
- `WAREHOUSE_WORKER`: просмотр товаров, складов, остатков и заказов; изменение существующих складских остатков.

Template-страницы учитывают роли: worker видит товары только в режиме чтения, а создание товаров и заказов доступно только `ADMIN` и `MANAGER`.

## Основные endpoints

- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `GET /api/users/me/`
- `CRUD /api/users/`
- `CRUD /api/categories/`
- `CRUD /api/products/`
- `CRUD /api/warehouses/`
- `CRUD /api/stock/`
- `CRUD /api/customers/`
- `CRUD /api/orders/`
- `POST /api/orders/{id}/change-status/`
- `GET /api/audit-log/`
- `GET /api/schema/`
- `GET /api/docs/`

Все API endpoints, кроме получения JWT, требуют `Authorization: Bearer <access>`.

## Template pages

- `/login/`
- `/dashboard/`
- `/products/`
- `/stock/`
- `/orders/`

Страницы используют Django session authentication. REST API использует JWT.

## Переменные окружения

Скопируйте пример:

```bash
cp .env.example .env
```

Основные переменные:

```text
DEBUG=True
SECRET_KEY=change-me-in-production-32-characters-minimum
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
DATABASE_URL=postgres://warehouse_user:warehouse_password@localhost:5432/warehouse_order
PORT=8000
```

## Локальный запуск

Установите Python 3.12 и PostgreSQL, создайте БД:

```sql
CREATE DATABASE warehouse_order;
CREATE USER warehouse_user WITH PASSWORD 'warehouse_password';
GRANT ALL PRIVILEGES ON DATABASE warehouse_order TO warehouse_user;
ALTER DATABASE warehouse_order OWNER TO warehouse_user;
```

Установите зависимости и примените миграции:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_data
```

Приложение будет доступно на `http://localhost:8000/`, Swagger на `http://localhost:8000/api/docs/`.

## Тестовые пользователи

Создаются командой `python manage.py seed_data`:

- `admin@example.com` / `Admin123!`
- `manager@example.com` / `Manager123!`
- `worker@example.com` / `Worker123!`

## Тесты

```bash
pytest
```

Тесты используют настройки Django и ожидают доступный PostgreSQL из `DATABASE_URL`.

## Swagger/OpenAPI

Swagger UI:

```text
http://localhost:8000/api/docs/
```

Генерация схемы:

```bash
python manage.py spectacular --file schema.yml
```

## Бизнес-логика заказов

- Создание заказа проверяет доступный остаток: `quantity - reserved_quantity`.
- Переход в `RESERVED` увеличивает `reserved_quantity`.
- Переход в `SHIPPED` уменьшает `quantity` и `reserved_quantity`.
- `CANCELLED` освобождает резерв, если заказ был `RESERVED`.
- `COMPLETED` заказ нельзя изменять, удалять или повторно переводить в другой статус.
- Критичные операции выполняются внутри `transaction.atomic()`.

## Fuzzing через Schemathesis

После запуска сервера:

```bash
schemathesis run http://localhost:8000/api/schema/
```

Цели и ожидаемые результаты описаны в `docs/fuzzing-report.md`.

## Deploy на Render или Railway

1. Создайте PostgreSQL service.
2. Добавьте web service из этого репозитория.
3. Укажите build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

4. Укажите start command:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

5. Задайте env vars: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PORT`.
   Для строгих production-настроек можно также задать `DJANGO_SETTINGS_MODULE=config.settings_production`.
6. Запустите release/admin commands:

```bash
python manage.py migrate
python manage.py seed_data
```

## Соответствие 12-Factor App

- Одна кодовая база: проект подготовлен как единый Django repository.
- Зависимости: описаны в `requirements.txt`.
- Конфигурация: только через `.env` и переменные окружения.
- Backing services: PostgreSQL подключается через `DATABASE_URL`.
- Build/release/run: Dockerfile собирает образ, миграции и `seed_data` запускаются отдельными admin processes, web запускается через gunicorn.
- Processes: приложение stateless; сессии хранятся в БД, не в памяти процесса.
- Port binding: web service слушает env `PORT`.
- Logs: Django пишет в stdout/stderr.
- Admin processes: `migrate`, `createsuperuser`, `seed_data` оформлены как management commands.
