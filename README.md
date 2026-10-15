# fish-modular

Шаблон бэкенда на FastAPI в стиле **модульного монолита**: Dishka DI, чистая архитектура,
JWT-аутентификация, CRUD пользователей. Функционально повторяет
[FastAPI-Fish](https://github.com/Wertiba/FastAPI-Fish), а архитектурно — упрощённый
[tmatch](https://github.com/sazsu/tmatch) без Kafka, медиатора и CQRS-бойлерплейта.

Цель — форкнуть и сразу пилить домены: `make module name=projects` за секунду даёт рабочий
модуль с CRUD, правами доступа, тестами и регистрацией в приложении.

## Что внутри

- **Auth**: register / login / refresh / logout. Access JWT + ротируемый refresh-токен в
  `HttpOnly`-куке; в БД хранится только SHA-256 хеш refresh-токена.
- **Users**: список с пагинацией и фильтрами, создание, чтение, обновление, деактивация.
  Роли `USER` / `ADMIN`, правила «только админ» и «админ или сам».
- **Bootstrap-админ** создаётся при старте из `APP_ADMIN_*`.
- **Ошибки** в едином формате: `code`, `message`, `traceId`, `timestamp`, `path`,
  а также `details` или `fieldErrors`. Это касается и 404/405, и необработанных 500.
- **Trace-id**: заголовок `X-Trace-Id` (принимается или генерируется), попадает в каждую строку лога.
- **Ops**: `/health/liveness`, `/health/readiness` (проверяет БД), `/metrics` (Prometheus).
- **Межмодульные события**: внутрипроцессные, в той же транзакции. Например, `users` публикует
  `UserDeactivated`, а `auth` в ответ отзывает сессии пользователя.
- **Swagger 1-в-1 с Fish**: те же пути, параметры, тела, коды ответов, `operationId` и имена
  схем (`UserReadResponse`, `Page_UserReadResponse_`…). Фронт, сгенерированный по Fish,
  работает без изменений; это закреплено контрактным тестом.
- **Качество**: uv + `uv.lock`, ruff, mypy `--strict`, архитектурные тесты границ модулей,
  e2e-тесты на SQLite и PostgreSQL, проверка миграций в CI.

## Быстрый старт

```bash
./scripts/init_project.sh "My Team"   # опционально: переименовать проект
cp .env.example .env                  # поменяйте секреты

# вариант 1: всё в Docker
docker compose up --build             # http://localhost:8080/docs

# вариант 2: локально (нужен uv: https://docs.astral.sh/uv/)
uv sync                               # .venv с Python 3.13 и всеми зависимостями по uv.lock
uv run alembic upgrade head           # нужен Postgres из .env
uv run python -m app                  # http://localhost:8080/docs
```

Все команды есть в `Makefile` (`make install`, `make run`, `make test`, `make check`…).
Зависимости добавляются через `uv add <пакет>` (dev — `uv add --dev <пакет>`), lock обновится сам.

Прототип без Postgres и миграций: `DB_URL=sqlite+aiosqlite:///./dev.db` и `DB_CREATE_TABLES=true`.

## Структура

```
src/app/
├── main.py                 create_app(): middleware, роутеры, DI, lifespan
├── bootstrap/              composition root — единственное место, где всё связывается
│   ├── config.py           Settings (env / .env)
│   ├── ioc.py              контейнер Dishka: конфиги, БД, сессия, транзакция, шина событий
│   └── logging.py          loguru + trace-id
├── shared/                 shared kernel: общее для всех модулей, ничего не знает о модулях
│   ├── domain/             базовые ошибки, Identity/UserRole, время
│   ├── application/        порты: IdentityProvider, TransactionManager, EventPublisher, Page
│   ├── infrastructure/     metadata/engine, imperative mapping, UtcDateTime, шина событий
│   ├── presentation/       обработчики ошибок, trace-id, CamelModel, пагинация, health/metrics
│   └── module.py           описание модуля (Module)
└── modules/
    ├── registry.py         MODULES = (auth_module, users_module, ...) — порядок = порядок в Swagger
    ├── users/
    └── auth/
```

### Устройство модуля

```
modules/users/
├── public.py          контракт для других модулей: UsersApi, UserInfo, UserDeactivated, UserReadResponse
├── domain/            сущности (чистые dataclass'ы) и доменные ошибки
├── application/       ports.py (Protocol'ы), commands.py, queries.py
├── infrastructure/    tables.py (Table + imperative mapping), repository.py, адаптеры
├── presentation/      router.py, schemas.py (camelCase)
├── ioc.py             Dishka Provider модуля
└── module.py          Module(name, providers, routers, map_tables, subscriptions)
```

Зависимости направлены внутрь: `presentation → application → domain`,
а `infrastructure` реализует порты из `application`. Правила проверяются тестом
`tests/architecture/test_boundaries.py`, так что CI упадёт, если их нарушить:

| Слой / место | Можно импортировать |
|---|---|
| `domain` | stdlib, `shared.domain`, свой `domain` |
| `application` | `domain`, `shared.application`, `public.py` других модулей (без FastAPI и SQLAlchemy) |
| другой модуль | только `app.modules.<x>.public` |
| `shared` | ничего из `modules` и `bootstrap` |

## Добавить домен

```bash
make module name=projects                 # или: uv run python scripts/new_module.py projects Project
make migration m="add projects"
make migrate
uv run pytest tests/e2e/test_projects.py
```

Генератор создаёт модуль с сущностью `Project` (`title`, `description`, `owner_id`) и CRUD
`/api/v1/projects`. Пользователь видит свои записи, админ — все. Также генерируются e2e-тест
и строка в `registry.py`. Дальше вы переделываете сущность под свою предметную область.

Ручной путь (если генератор не подходит):
1. Сущность в `domain/entities.py`, ошибки в `domain/errors.py` (наследуйте от категорий в
   `shared/domain/errors.py`; HTTP-статус подберётся сам).
2. Порты в `application/ports.py`, интеракторы в `commands.py` и `queries.py`.
3. Таблица и `map_tables()` в `infrastructure/tables.py`, репозиторий в `repository.py`.
4. Роутер со схемами, `ioc.py`, `module.py`, строка в `modules/registry.py`.

## Как писать код

**Интерактор** — это класс с `__call__`, зависимости приходят через `__init__`, а роутер получает его
через `FromDishka[...]`. Команда в конце вызывает `await self._tx.commit()`. Запрос ничего не коммитит.

```python
class CreateUser:
    def __init__(self, idp: IdentityProvider, registrar: UserRegistrar, tx: TransactionManager): ...

    async def __call__(self, *, email: str, ...) -> User:
        actor = await self._idp.get_identity()   # текущий пользователь или 401
        actor.require_admin()                     # 403
        user = await self._registrar.register(...)
        await self._tx.commit()
        return user
```

**Текущий пользователь** берётся из `IdentityProvider` (порт в shared, реализация в `auth`).
Модулям не нужно знать про JWT и заголовки.

**Транзакция** одна на HTTP-запрос: все репозитории и обработчики событий работают в одной
сессии. Без `commit()` изменения откатятся.

**Связь между модулями** бывает двух видов:
- *синхронный вызов* через фасад из `public.py`. Например, `auth` вызывает
  `UsersApi.authenticate()`. Реализация живёт в `application/public_api.py` и регистрируется в `ioc.py`;
- *событие*: класс события объявляется в `public.py` модуля-источника, публикуется через
  `EventPublisher`, а подписка оформляется в `module.py` модуля-подписчика:

```python
# modules/auth/module.py
subscriptions = {UserDeactivated: [RevokeSessionsOnUserDeactivated]}
```

**Ошибки**: `raise ProjectNotFoundError` в любом слое превращается в 404 в общем формате.
Категории и их статусы: `NotFoundError` 404, `ConflictError` 409, `AuthenticationError` 401,
`AccessDeniedError` 403, `BusinessRuleError` 422, `LockedError` 423.

**Таблицы** описываются через `sa.Table` и привязываются к dataclass-сущностям через imperative mapping.
В домене нет SQLAlchemy, а ORM всё равно отслеживает изменения: изменили поле сущности,
вызвали `commit()`, и изменение сохранилось.

## API

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/api/v1/auth/register` | все — 201, токен + refresh-кука + `Location` |
| POST | `/api/v1/auth/login` | все |
| POST | `/api/v1/auth/refresh` | refresh-кука — ротация пары токенов |
| POST | `/api/v1/auth/logout` | refresh-кука — 204 |
| GET | `/api/v1/users` | admin — `page`, `size`, `email`, `fullName`, `role`, `isActive`, `createdFrom`, `createdTo` |
| POST | `/api/v1/users` | admin |
| GET, PUT | `/api/v1/users/me` | авторизованный |
| GET, PUT | `/api/v1/users/{id}` | admin или сам (роль и активность меняет только admin) |
| DELETE | `/api/v1/users/{id}` | admin — деактивация + отзыв сессий |
| GET | `/health/liveness`, `/health/readiness`, `/metrics` | все |

Swagger UI — `/docs`. Схема совпадает с FastAPI-Fish байт в байт; эталон лежит в
`tests/contract/fish_openapi.json`, а `tests/contract/test_fish_openapi.py` падает при любом
расхождении в путях и схемах Fish. Новые домены добавляют свои пути, это не нарушение.
Сгенерированные модули объявляют Bearer-security, поэтому для их эндпоинтов в Swagger появляется
кнопка Authorize. Выгрузка схемы для фронта: `make openapi` → `docs/openapi.json`.

## Конфигурация

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | — | PostgreSQL |
| `DB_URL` | — | полный URL, перекрывает `DB_*` |
| `DB_CREATE_TABLES` | `false` | `create_all` при старте (прототипы, тесты) |
| `APP_SECURITY_JWT_SECRET` | **обязательно** | подпись JWT |
| `APP_SECURITY_ACCESS_TOKEN_EXPIRATION` / `..._REFRESH_...` | `15m` / `30d` | TTL токенов |
| `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD`, `APP_ADMIN_FULLNAME` | — | bootstrap-админ |
| `APP_COOKIE_SECURE` | `true` | `Secure` у refresh-куки (для http выставьте `false`) |
| `APP_CORS_ALLOWED_ORIGINS` | localhost | через запятую |
| `LOG_LEVEL`, `LOG_FILE` | `INFO`, `logs/app.log` | пустой `LOG_FILE` отключает запись в файл |

Модули не читают `Settings` напрямую: `bootstrap/ioc.py` собирает из них маленькие конфиги
(`AuthConfig`, `DatabaseConfig`). Новому модулю нужен свой конфиг? Добавьте dataclass в модуль
и `@provide` в `ConfigProvider`.

## Тесты

```bash
make test                                                          # SQLite in-memory, без Docker
make test-pg DB=postgresql+asyncpg://postgres:postgres@localhost/app_test   # отдельная БД!
make check                                                         # ruff + mypy + тесты
```

- `tests/e2e/` — HTTP-сценарии через `TestClient` (фикстуры `client`, `admin_headers`, `register_user`);
- `tests/unit/` — домен и интеракторы на фейках портов, без БД;
- `tests/architecture/` — правила импортов между модулями и слоями;
- `tests/contract/` — OpenAPI совпадает с FastAPI-Fish.

Для `TEST_DB_URL` используйте отдельную базу: тесты удаляют таблицы после каждого прогона.
