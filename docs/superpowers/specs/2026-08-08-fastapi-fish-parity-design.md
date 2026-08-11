# FastAPI-Fish: приведение к паритету с KotlinFish

Дата: 2026-08-08
Статус: одобрено пользователем, готовится план реализации

## Контекст

Репозиторий `FastAPI-Fish` должен стать функциональным аналогом эталонного шаблона
[`KotlinFish`](https://github.com/Wertiba/KotlinFish) (Kotlin + Spring Boot 4): тот же API-контракт,
та же схема БД, тот же уровень универсальности (переиспользуемый шаблон), но на FastAPI.

Аудит текущего кода показал, что он собран из набросков как минимум трёх разных прошлых проектов
и в текущем виде не запускается:

- `UnitOfWork` импортирует несуществующие репозитории (`FlagRepository`, `ExperimentRepository`,
  `DecisionRepository`, `ApproverRepository`, `ReviewRepository`, `EventRepository`,
  `RoleRepository`, `MetricRepository`) — файлов этих репозиториев нет.
- `UserRepository.get_by_email/get_paginated` обращаются к `User.roles`, которого нет в модели
  (`User.role` — одиночный enum, не список).
- `UserRole.ADMN` — опечатка вместо `ADMIN` (используется в нескольких местах).
- `UserService.get_all_users/get_by_id` не имеет метода `get_current_by_id`, который вызывают
  эндпоинты `users.py` — рантайм-ошибка на каждый вызов `/users/me`, `/users/{id}`.
- `configs/config.yaml` содержит настройки от другого проекта (`app.name: NoteManager`, кэш
  фиче-флагов, `exp_index` и т.д.), не относящиеся к Fish-домену.
- Эндпоинтов `register`, `refresh`, `logout` нет вообще — есть только `login`.
- Таблицы `refresh_tokens` нет — refresh-токены нигде не хранятся и не ротируются.
- `src/README.md` пустой, `.env.example` нет, `server.pas` и
  `tests/LottyABPlatform.postman_collection.json` — мусор от другого проекта.

Дизайн ниже описывает целевое поведение — реализация будет поэтапной (см. раздел «Этапы»).

## Цели

- Полный паритет по API-контракту, схеме БД и поведению с `KotlinFish`.
- Репозиторий остаётся переиспользуемым шаблоном (аналог "Use this template" в Kotlin-версии):
  генерик-документация, `.env.example`, скрипт переименования проекта.
- Полный набор возможностей, а не только core: health/readiness, `X-Trace-Id`, Prometheus-метрики,
  структурные логи, CI.
- Тексты ошибок/валидации — на английском, по образцу Kotlin-версии.
- Тесты — интеграционные, на реальном Postgres (docker), как `*IT.kt` в Kotlin-версии.

## Не цели

- Точное копирование Java/Kotlin-специфичных вещей, для которых в Python/FastAPI просто нет
  прямого аналога (Spring Actuator как фреймворк, JPA Specifications как технология,
  ktlint/JaCoCo). Вместо этого — функционально эквивалентная замена (см. «Observability»).
- Поддержка нескольких форматов структурных логов (`ecs`/`gelf`/`logstash`) — будет один
  переключатель `LOG_FORMAT=json|text`, покрывающий тот же сценарий (человекочитаемые логи в
  консоли, JSON — по флагу).

## Архитектура

Сохраняется текущее послойное деление (`api` → `services` → `unit_of_work` → `repositories` →
`models`), но с чётким разделением, которого сейчас не хватает:

- **Модели БД** (`app/infrastructure/models`) — SQLAlchemy 2.0 declarative, колонки в snake_case,
  1:1 с DDL ниже. Больше не наследуются от `SQLModel`/`PyModel` — это persistence-слой, не API.
- **API-схемы** (`app/core/schemas`) — Pydantic v2 `BaseModel` с `alias_generator` в camelCase
  (`ConfigDict(populate_by_name=True, from_attributes=True)`), полностью независимы от ORM-класса.

Это устраняет корень нынешней путаницы: поля модели были в camelCase (потому что схема и модель —
один и тот же SQLModel-класс), из-за чего колонки в БД не совпадали со snake_case из DDL.

`UnitOfWork` содержит только `user_repo` и `refresh_token_repo` — все репозитории от чужого домена
(flags/experiments/decisions/...) удаляются вместе с файлами, которые их когда-то содержали (их и
так уже нет — только мёртвые импорты).

## Схема БД

Точное соответствие `V1__init.sql` из Kotlin-версии, через Alembic-миграцию:

```sql
CREATE TABLE users
(
    id         UUID PRIMARY KEY,
    email      VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    full_name  VARCHAR(255) NOT NULL,
    role       VARCHAR(20)  NOT NULL CHECK (role IN ('USER', 'ADMIN')),
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL
);

CREATE TABLE refresh_tokens
(
    id           UUID PRIMARY KEY,
    user_id      UUID                        NOT NULL REFERENCES users (id),
    hashed_token VARCHAR(255)                NOT NULL,
    expires_at   TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    created_at   TIMESTAMP(6) WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_hashed_token ON refresh_tokens (hashed_token);
```

`created_by` по умолчанию указывает на самого пользователя (self-reference), если явно не задан —
поведение уже частично реализовано в текущей модели через `model_validator`, будет перенесено в
сервис (после `INSERT` id уже известен).

## Auth-флоу

Мирроринг `AuthController`/`AuthService`/`JWTService` из Kotlin:

| Endpoint | Метод | Публичный | Действие |
|---|---|---|---|
| `/api/v1/auth/register` | POST | да | создаёт пользователя с role=USER, 201, `Location: /api/v1/users/{id}`, ставит cookie `refreshToken`, тело `UserAndAccessTokenResponse` |
| `/api/v1/auth/login` | POST | да | 200, та же cookie+тело |
| `/api/v1/auth/refresh` | POST | да (нужна cookie) | читает `refreshToken` из cookie, ротирует, 200 `AccessTokenResponse` |
| `/api/v1/auth/logout` | POST | да (нужна cookie) | удаляет refresh-запись по хэшу, 204, чистит cookie |

Токены:

- **Access token** — JWT (HS256), claims `sub`, `type=access`, `jti`, `iat`, `exp`. Живёт только в
  теле ответа / заголовке `Authorization: Bearer`. Нигде не хранится на сервере. Cookie-fallback
  для access-токена, который есть в текущем коде, убирается — в контракте Kotlin access-token в
  cookie никогда не попадает.
- **Refresh token** — JWT с `type=refresh`, плюс SHA-256-хэш сырого токена сохраняется в
  `refresh_tokens` (userId, hashedToken, expiresAt). При `/refresh`: валидация JWT → поиск по
  `(user_id, hashed_token)` → если не найден или истёк — 401 → старая запись удаляется, выпускается
  и сохраняется новая (ротация). При `/logout` — удаление записи по хэшу (идемпотентно). При
  деактивации пользователя (`isActive: true → false`) — удаляются все refresh-записи этого
  пользователя (принудительный logout всех сессий), как `revokeSessionsIfJustDeactivated` в Kotlin.
- Cookie `refreshToken`: `HttpOnly`, `Secure` (флаг из `APP_COOKIE_SECURE`, default `true`),
  `SameSite=Lax`, `Path=/`, `Max-Age` = refresh-TTL.

Хэширование паролей — реализационная деталь, не часть контракта: остаётся argon2 (уже используется,
менять не нужно).

## Users API

| Endpoint | Метод | Доступ | Действие |
|---|---|---|---|
| `/api/v1/users` | GET | ADMIN | пагинация + фильтры, см. ниже |
| `/api/v1/users` | POST | ADMIN | создание пользователя с произвольной ролью |
| `/api/v1/users/me` | GET | любой аутентифицированный | текущий пользователь |
| `/api/v1/users/me` | PUT | любой аутентифицированный | обновление себя (см. ограничение ниже) |
| `/api/v1/users/{id}` | GET | ADMIN или self | чтение |
| `/api/v1/users/{id}` | PUT | ADMIN или self | обновление (см. ограничение ниже) |
| `/api/v1/users/{id}` | DELETE | ADMIN | soft-delete (`isActive=false`) + отзыв всех refresh-токенов |

Пагинация/фильтры на `GET /users` (`UserFilterQuery` в Kotlin):

- `page` (default 0, ≥0), `size` (default 20, 1..100)
- `email`, `fullName` — contains, case-insensitive
- `role`, `isActive` — точное совпадение
- `createdFrom`, `createdTo` — диапазон по `createdAt`
- Сортировка: `isActive desc, createdAt desc`
- Ответ: `PageResponse{items, total, page, size}`

Правило владения при `PUT` (self или admin): менять `role`/`isActive` может только ADMIN; если
не-ADMIN пытается прислать значение, отличное от текущего — 403 `FORBIDDEN`.

`UserReadResponse`: `id, email, fullName, role, isActive, createdAt, updatedAt, createdBy` —
все поля camelCase, даты в ISO-8601 с `Z`.

## Ошибки и валидация

Единая форма ответа об ошибке (`ErrorResponse`, non-null поля сериализуются, остальные опускаются):

```
{ code, message, traceId, timestamp, path, details?, fieldErrors? }
```

Коды ошибок 1:1 с Kotlin (`DOMAIN_TO_API` map приводится в соответствие):

| Код | HTTP | Когда |
|---|---|---|
| `EMAIL_ALREADY_EXISTS` | 409 | регистрация/создание с занятым email (`details: {field: "email", value}`) |
| `NOT_FOUND` | 404 | пользователь не найден |
| `UNAUTHORIZED` | 401 | неверные креды, невалидный/просроченный токен, отсутствует cookie |
| `FORBIDDEN` | 403 | недостаточно прав / чужой ресурс |
| `USER_INACTIVE` | 423 | деактивированный пользователь пытается пройти аутентификацию |
| `VALIDATION_FAILED` | 422 | ошибки валидации тела/параметров (`fieldErrors` заполнен) |

Домены из старого проекта (`DeficiencyApproversError` и т.п.) удаляются из `exc_map.py`.

Правила валидации (регэкспы 1:1 из `UserConstraints.kt`, сообщения на английском):

- `email`: валидный email, ≤254 символов.
- `password`: `^(?=.*[A-Za-z])(?=.*\d).{8,72}$`
- `fullName`: `^[а-яА-Яa-zA-Z0-9 _-]{2,200}$`

`X-Trace-Id`: middleware читает заголовок запроса (или генерирует uuid4), кладёт в contextvar,
проставляет на **каждый** ответ (не только ошибки — сейчас так только в error-хендлере), и
подставляет в `ErrorResponse.traceId`.

## Observability и bootstrap

Функциональные аналоги Spring Actuator (прямого аналога у FastAPI нет — see «Не цели»):

- `GET /api/v1/health/liveness` — всегда 200.
- `GET /api/v1/health/readiness` — 200 если БД доступна, иначе 503 + `checks`.
- `GET /api/v1/metrics` — Prometheus exposition format (`prometheus_client`/`prometheus-fastapi-instrumentator`).

Bootstrap администратора — переносится из ручного `run.py`-скрипта в FastAPI `lifespan`-хук:
запускается автоматически при каждом старте приложения (как `AdminInitializer` в Kotlin —
`ApplicationRunner`), читает `APP_ADMIN_EMAIL/PASSWORD/FULLNAME`, создаёт admin-пользователя если
его ещё нет, логирует результат.

## Конфигурация

Имена переменных окружения переносятся из Kotlin-версии (где нет прямого Python-эквивалента —
ближайший функциональный аналог):

| Переменная | Назначение |
|---|---|
| `DB_URL`/`DB_HOST`,`DB_PORT`,`DB_USER`,`DB_PASSWORD`,`DB_NAME` | подключение к Postgres |
| `APP_SECURITY_JWT_SECRET` | секрет подписи JWT |
| `APP_SECURITY_ACCESS_TOKEN_EXPIRATION` | TTL access-токена (формат `15m`, default `15m`) |
| `APP_SECURITY_REFRESH_TOKEN_EXPIRATION` | TTL refresh-токена (формат `30d`, default `30d`) |
| `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD`, `APP_ADMIN_FULLNAME` | bootstrap-администратор |
| `APP_CORS_ALLOWED_ORIGINS` | CSV origin-ов для CORS |
| `APP_COOKIE_SECURE` | `Secure`-флаг у refresh-cookie (default `true`) |
| `LOG_FORMAT` | `text` (default) или `json` |

Из `config.yaml`/Dynaconf убирается весь мусор от других проектов (`app.name: NoteManager`, кэш
фиче-флагов, `exp_index`, `restrictions`).

## Очистка

Удаляются полностью:
- `app/infrastructure/repositories/*` от чужого домена и их мёртвые импорты в `__init__.py`/`UnitOfWork`.
- `server.pas` (посторонний health-сервер на Pascal).
- `tests/LottyABPlatform.postman_collection.json`.

Исправляются:
- `UserRole.ADMN` → `UserRole.ADMIN` везде.
- `UserService` — `get_current_by_id` (которого нет, но который вызывают эндпоинты) удаляется;
  эндпоинты переходят на существующий `get_by_id`, а проверка "ADMIN или self" переносится в
  FastAPI-зависимость (`AdminOrSelfDep`), как `@PreAuthorize("hasRole('ADMIN') or #id == principal.id")`
  в Kotlin.
- `UserRepository` — убираются обращения к несуществующему `User.roles`, добавляется построение
  фильтров для `GET /users`.

## Шаблонизация

Поскольку репозиторий остаётся переиспользуемым шаблоном (аналог "Use this template" в Kotlin):

- `src/README.md` — по структуре Kotlin `README.md`: features, tech stack, "using this as a
  template", repo map, таблица конфигурации, команды, API overview.
- `.env.example` — коммитится с плейсхолдер-значениями (сейчас есть только `.env`, гитигнорится).
- Скрипт переименования (`actions/init-project.sh` + `.ps1`) — переименовывает то, что в FastAPI
  является аналогом Kotlin-пакета: имя приложения (`Settings`/`app.name`), имена
  сервиса/volume/container в `docker-compose.yml`, путь лог-файла. Инструкция — удалить скрипты
  после использования, как в Kotlin-версии.
- `docs/api-docs.json` — экспорт `openapi.json` из FastAPI (аналог статического экспорта спеки в
  Kotlin-версии).

## Тесты и CI

- Интеграционные тесты на реальном Postgres через docker (fixture поднимает контейнер или
  переиспользует `docker-compose`), покрывающие: полный auth-флоу с ротацией refresh-токена,
  users CRUD, RBAC/ownership-правила, валидацию, пагинацию и фильтры — аналог `AuthControllerIT` /
  `UserControllerIT`.
- Юнит-тесты для JWT-сервиса и сервисов домена (аналог `JWTServiceTest`/`UserServiceTest`).
- `.github/workflows/ci.yml`: `ruff check` (аналог `ktlintCheck`) + `pytest` с Postgres-сервисом в
  CI, на каждый push/PR в `main`.

## Этапы реализации

1. Чистка мусора и починка `UnitOfWork`/сервисов, чтобы приложение вообще запускалось.
2. Модель БД (SQLAlchemy, snake_case) + Alembic-миграция 1:1 с DDL.
3. Auth-флоу: JWT access/refresh, `refresh_tokens`, ротация, cookie-хелпер, 4 эндпоинта.
4. Users CRUD: пагинация, фильтры, RBAC/ownership, soft-delete.
5. Ошибки и валидация: единый `ErrorResponse`, коды, регэкспы, `X-Trace-Id` middleware.
6. Observability: health/readiness/metrics, admin bootstrap на старте приложения.
7. Шаблонизация: README, `.env.example`, скрипт переименования, экспорт OpenAPI.
8. Тесты (unit + integration на Postgres) и CI.
