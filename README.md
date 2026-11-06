# FastAPI-Fish

Шаблон бэкенда на FastAPI в стиле **гибридной чистой архитектуры** со слоями
`domain → application → infra / presentation`: Dishka DI, JWT-аутентификация, CRUD пользователей.
Гибрид: зависимости направлены внутрь, как в чистой архитектуре, но сущность — сразу декларативная
модель SQLAlchemy, а входы use case — Pydantic-схемы. Поэтому поле описывается в 3–4 местах, а не в 15.
Структура повторяет бэкенд [PetCare](https://github.com/Wertiba/PetCare-PROD-Hackathon-2026),
а API — [FastAPI-Fish](https://github.com/Wertiba/FastAPI-Fish) (контракт закреплён тестом).

Цель — форкнуть и сразу пилить домены: `make domain name=projects` за секунду раскладывает
по всем слоям рабочий CRUD с правами доступа, тестами и регистрацией в приложении.

## Что внутри

- **Auth**: register / login / refresh / logout. Access JWT + ротируемый refresh-токен в
  `HttpOnly`-куке; в БД хранится только SHA-256 хеш refresh-токена.
- **Users**: список с пагинацией и фильтрами, создание, чтение, обновление, деактивация.
  Роли `USER` / `ADMIN`, правила «только админ» и «админ или сам». Деактивация отзывает все сессии.
- **Админ** создаётся при старте из `ADMIN_*`, если такого email ещё нет.
- **Ошибки** в едином формате: `code`, `message`, `traceId`, `timestamp`, `path`,
  а также `details` или `fieldErrors`. Это касается и 404/405, и необработанных 500.
- **Trace-id**: заголовок `X-Trace-Id` (принимается или генерируется), попадает в каждую строку лога.
- **Логи**: одна JSON-строка на событие в stdout, только известные события без пользовательских
  данных (`infra/logger.py`).
- **Ops**: `/health/liveness`, `/health/readiness` (проверяет БД), `/metrics` (Prometheus:
  запросы по шаблонам маршрутов, задержки, бизнес-события через `track()`).
- **Swagger 1-в-1 с Fish**: те же пути, параметры, тела, коды ответов, `operationId` и имена
  схем (`UserReadResponse`, `Page_UserReadResponse_`…). Фронт, сгенерированный по Fish,
  работает без изменений.
- **Качество**: uv + `uv.lock`, ruff, mypy `--strict`, архитектурный тест слоёв,
  тесты на SQLite и PostgreSQL, проверка миграций в CI.

## Быстрый старт

```bash
./scripts/init_project.sh "My Team"   # опционально: переименовать проект
cp src/.env.example src/.env          # поменяйте секреты

# вариант 1: всё в Docker
docker compose up --build             # http://localhost:8080/docs

# вариант 2: локально (нужен uv: https://docs.astral.sh/uv/)
uv sync                               # .venv с Python 3.13 и всеми зависимостями по uv.lock
make migrate                          # нужен Postgres из src/.env
make run                              # http://localhost:8080/docs
```

Приложение и Alembic читают **только переменные окружения процесса**. `src/.env` подхватывают
`make` (`uv run --env-file src/.env ...`) и `docker compose` (`env_file`); тестам он не нужен.

Все команды есть в `Makefile` (`make install`, `make run`, `make test`, `make check`…).
Зависимости добавляются через `uv add <пакет>` (dev — `uv add --dev <пакет>`), lock обновится сам.

## Структура

```
src/app/
├── main.py              create_app(): middleware, роутеры, обработчики ошибок, lifespan; app = create_app()
├── bootstrap.py         build_container(): все Dishka-провайдеры — единственное место сборки
├── run.py               python -m app.run (локальный запуск)
├── domain/              сущности = декларативные модели SQLAlchemy (они же таблицы) и доменные ошибки
│   ├── base.py          Base (MappedAsDataclass), UtcDateTime, str_enum, naming convention
│   ├── errors.py        EntityError — база доменных ошибок
│   ├── users/           entity.py, enums.py, errors.py
│   └── refresh_tokens/
├── application/         сценарии; без FastAPI и infra (SQLAlchemy — только через модели domain)
│   ├── ports/           Protocol'ы: *_gateway.py, unit_of_work.py, tokens.py, database_health.py
│   ├── auth/            interactors.py, dto.py (результаты с токенами), di.py
│   ├── users/           interactors.py, schemas.py (входы = тела запросов), password.py, access.py, di.py
│   ├── schema.py        PyModel: поля snake_case, в JSON и OpenAPI — camelCase-алиасы
│   ├── pagination.py, changes.py, exceptions.py
├── infra/               реализации портов
│   ├── config.py, di.py конфиги из окружения (RunConfig, DatabaseConfig, SecurityConfig…) и их провайдер
│   ├── database/        __init__.py (импорт всех моделей и metadata для Alembic), unit_of_work.py, db_helper.py, health.py
│   ├── gateways/        SqlAlchemy*Gateway + GatewayProvider
│   ├── security/        JWTService: JWT, argon2, хеш refresh-токена
│   ├── logger.py, metrics.py, duration.py
└── presentation/http/
    ├── api/endpoints/   health, metrics (вне /api)
    ├── api/v1/          endpoints/, dependencies/ (CurrentUserDep, PaginationDep), exceptions/, utils/cookies.py
    ├── schemas/         схемы ответов (UserReadResponse…) и ошибок
    ├── middleware/      trace_id.py (X-Trace-Id + 500), observability.py (метрики + access-лог)
    └── paginated.py, loc2field.py

src/alembic.ini, src/alembic/   миграции; env.py берёт DatabaseConfig и metadata из infra/database/__init__.py
```

Зависимости направлены внутрь. Правила проверяет `tests/architecture/test_architecture.py`,
так что CI упадёт, если их нарушить:

| Слой | Можно импортировать |
|---|---|
| `domain` | stdlib, `sqlalchemy` (декларативные модели) и сам `domain` |
| `application` | `domain`, `application`, `pydantic`; `dishka` — только в `application/*/di.py` |
| `infra` | `domain`, `application`, `infra` (не `presentation`) |
| `presentation` | всё, кроме composition root (`bootstrap.py`, `main.py`, `run.py`) |

## Добавить домен

```bash
make domain name=projects                 # или: uv run python scripts/new_domain.py projects Project
make migration m="add projects"
make migrate
uv run pytest tests/api/test_projects_endpoints.py
```

Генератор раскладывает по слоям сущность `Project` (`title`, `description`, `owner_id`) и CRUD
`/api/v1/projects` (`GET`, `POST`, `GET/PATCH/DELETE /{id}`). Пользователь видит свои записи,
админ — все. Генерируются тест и регистрация в общих точках сборки, а `docs/openapi.json`
обновляется. Дальше вы переделываете сущность под свою предметную область.

Ручной путь (если генератор не подходит):
1. `domain/<x>/`: `entity.py` (модель `class X(Base, kw_only=True)`), `errors.py` (наследники `EntityError`).
2. `application/ports/<x>_gateway.py` и `application/<x>/`: `schemas.py`, `interactors.py`, `di.py`.
3. Импорт модели и её имя в `__all__` в `infra/database/__init__.py`, чтобы Alembic увидел таблицу.
4. `infra/gateways/<x>.py` + строка в `infra/gateways/di.py`.
5. `presentation/http/schemas/<x>.py`, `presentation/http/api/v1/endpoints/<x>.py` + `include_router`
   в `endpoints/__init__.py`; ошибки → `exceptions/exc_map.py`.
6. Провайдер интеракторов в `bootstrap.py`.

## Как писать код

**Интерактор** — класс с `__call__`; общие зависимости собраны в dataclass-контексте, и Dishka
передаёт их в конструктор. Эндпоинт получает интерактор через `FromDishka[...]`, а текущего
пользователя — через `CurrentUserDep`, и передаёт `user.id` в интерактор. Команда в конце вызывает
`await self.uow.commit()`; запрос ничего не коммитит.

```python
@dataclass
class _UserContext:
    uow: UnitOfWork
    user_gateway: UserGateway
    ...

class CreateUser(_UserContext):
    async def __call__(self, user_id: UUID, data: AdminRegisterUserBody) -> User:
        await require_admin(self.user_gateway, user_id)   # роль читается из БД -> 403
        user = User(**data.model_dump(exclude={"password"}), password_hash=..., created_by=user_id)
        await self.uow.add(user)
        await self.uow.commit()                            # DuplicateError -> 409
        return user
```

Интерактор принимает Pydantic-схему (она же тело запроса) и возвращает модель. JSON собирает
`response_model` эндпоинта через `from_attributes`, так что перекладывать поля в DTO не нужно.
Имена полей схем совпадают с полями модели (snake_case), а наружу видны camelCase-алиасы:
`full_name` в коде — `fullName` в API.

**Транзакция** одна на HTTP-запрос: все gateways и `UnitOfWork` работают в одной сессии.
Без `commit()` изменения откатятся.

**Ошибки**: интерактор бросает доменную ошибку (`raise ProjectNotFoundError`), а
`presentation/http/api/v1/exceptions/exc_map.py` превращает её в API-ошибку (`NotFound`, `Forbidden`…
из `api_exs.py`) с нужным статусом и `code`. `DuplicateError` из `UnitOfWork.commit()` → 409,
прочие `ApplicationError` → 500 с записью в лог, ошибка без маппинга → 500 и `unmapped_domain_error`.

**Сущность = таблица**: модель в `domain/<x>/entity.py` наследует `Base` (`MappedAsDataclass`),
поэтому её можно создать без сессии (так работают unit-тесты на фейках), а ORM отслеживает изменения:
изменили поле, вызвали `commit()`, изменение сохранилось. Новое поле — это модель, миграция, нужные
входные схемы и схема ответа.

**Логи**: `logger.info("event_name", extra={...})`, где событие и его поля заранее перечислены в
`infra/logger.py`. Свободный текст и данные запросов в лог не попадают.

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

Swagger UI — `/docs`. Эталон схемы Fish лежит в `tests/contract/fish_openapi.json`, а
`tests/contract/test_fish_openapi.py` падает при любом расхождении в путях и схемах Fish.
Новые домены добавляют свои пути, это не нарушение. Выгрузка схемы для фронта:
`make openapi` → `docs/openapi.json` (тест сверяет её с приложением).

## Конфигурация

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | **обязательно** | PostgreSQL |
| `DB_PORT`, `DB_DRIVER` | `5432`, `postgresql+asyncpg` | |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `20`, `10` | пул соединений |
| `APP_SECURITY_JWT_SECRET` | **обязательно** | подпись JWT |
| `APP_SECURITY_ACCESS_TOKEN_EXPIRATION` / `..._REFRESH_...` | `15m` / `30d` | TTL токенов |
| `APP_SECURITY_ALGORITHM` | `HS256` | алгоритм JWT |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME` | — | админ при старте (если заданы email и пароль) |
| `APP_COOKIE_SECURE` | `true` | `Secure` у refresh-куки (для http выставьте `false`) |
| `APP_CORS_ALLOWED_ORIGINS` | localhost | через запятую |
| `RUN_HOST`, `RUN_PORT` | `0.0.0.0`, `8080` | `make run` |
| `LOG_CONSOLE_LEVEL`, `LOG_ENV`, `LOG_SYSTEM`, `LOG_INST` | `INFO`, `dev`, `app`, hostname | поля JSON-логов |

Каждая группа — свой Pydantic-конфиг в `infra/config.py`, который `ConfigProvider` (`infra/di.py`)
собирает из окружения. Новому домену нужен конфиг? Добавьте класс в `config.py` и `@provide` в
`ConfigProvider`.

## Тесты

```bash
make test                                                          # SQLite in-memory, без Docker
make test-pg DB=postgresql+asyncpg://postgres:postgres@localhost/app_test   # отдельная БД!
make check                                                         # ruff + mypy + тесты
```

- `tests/api/` — HTTP-сценарии через `TestClient` (фикстуры `client`, `admin_headers`, `register_user`);
  БД подменяется через Dishka-провайдер с `override=True`;
- `tests/unit/` — интеракторы на фейках портов, без БД;
- `tests/architecture/` — правила импортов между слоями и актуальность `docs/openapi.json`;
- `tests/contract/` — OpenAPI совпадает с FastAPI-Fish.

Для `TEST_DB_URL` используйте отдельную базу: тесты удаляют таблицы после каждого прогона.
