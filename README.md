# FastAPI-Fish

Шаблон бэкенда на FastAPI — **модульный монолит**: приложение делится на модули по предметным
областям (`auth`, `users`, …), а внутри каждого модуля — слои чистой архитектуры
`domain → application → infra / presentation`. Dishka DI, JWT-аутентификация, CRUD пользователей.

Рассчитан на много модулей и тяжёлую инфраструктуру: **четыре процесса из одного образа**
(`api`, `worker`, `scheduler`, `bot`) и готовые порты с адаптерами для **Kafka** (outbox/inbox),
**Redis**, **S3/MinIO**, **Telegram**, **Ollama**, **push в мобильное приложение (FCM)**. Каждая
внешняя система необязательна: пока её адрес не задан, работает локальная замена, так что шаблон
запускается и тестируется с одним Postgres.
Структура повторяет бэкенд [PetCare](https://github.com/Wertiba/PetCare-PROD-Hackathon-2026),
а API — [FastAPI-Fish](https://github.com/Wertiba/FastAPI-Fish) (контракт закреплён тестом).

Цель — форкнуть и сразу пилить модули: `make module name=projects` за секунду создаёт модуль
с рабочим CRUD, правами доступа, тестами и регистрацией в приложении.

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
  данных (`shared/infra/logger.py`).
- **Ops**: `/health/liveness`, `/health/readiness` (проверяет БД), `/metrics` (Prometheus:
  запросы по шаблонам маршрутов, задержки, бизнес-события через `track()`).
- **Swagger 1-в-1 с Fish**: те же пути, параметры, тела, коды ответов, `operationId` и имена
  схем (`UserReadResponse`, `Page_UserReadResponse_`…). Фронт, сгенерированный по Fish,
  работает без изменений.
- **Процессы** (`python -m app.run <process>`): `api` — сайт и мобильное приложение; `worker` —
  outbox → Kafka и консьюмеры; `scheduler` — периодические задачи модулей; `bot` — Telegram.
- **События**: в той же транзакции (`subscriptions`) или позже в worker (`consumers`) через
  outbox → Kafka (без Kafka — напрямую своим консьюмерам), с inbox для идемпотентности.
- **Мобильное приложение**: минимальная версия (`X-App-Version` → 426), push через FCM,
  прямые загрузки в S3 по presigned URL.
- **Качество**: uv + `uv.lock`, ruff, mypy `--strict`, архитектурные тесты модулей и слоёв,
  тесты на SQLite и PostgreSQL, проверка миграций в CI.

## Быстрый старт

```bash
./scripts/init_project.sh "My Team"   # опционально: переименовать проект
cp src/.env.example src/.env          # поменяйте секреты

# вариант 1: всё в Docker — api, worker, scheduler + Postgres, Redis, Kafka, MinIO
docker compose up --build -d                  # http://localhost:8080/docs, MinIO: http://localhost:9001
docker compose --profile telegram up -d       # + bot (нужен TELEGRAM_BOT_TOKEN)
docker compose --profile llm up -d            # + Ollama; модель: docker compose exec ollama ollama pull qwen2.5:7b

# вариант 2: процессы локально (нужен uv: https://docs.astral.sh/uv/)
uv sync                               # .venv с Python 3.13 и всеми зависимостями по uv.lock
make infra                            # опционально: Postgres, Redis, Kafka, MinIO в Docker
make migrate                          # нужен Postgres из src/.env
make run-api                          # http://localhost:8080/docs
make run-worker                       # в соседних терминалах, если нужны события и задачи
make run-scheduler
make run-bot
```

Приложение и Alembic читают **только переменные окружения процесса**. `src/.env` подхватывают
`make` (`uv run --env-file src/.env ...`) и `docker compose` (`env_file`); тестам он не нужен.

Все команды есть в `Makefile` (`make install`, `make run`, `make test`, `make check`…).
Зависимости добавляются через `uv add <пакет>` (dev — `uv add --dev <пакет>`), lock обновится сам.

## Структура

```
src/app/
├── bootstrap.py         MODULES — список модулей; build_container() — один DI-граф для всех процессов
├── run.py               python -m app.run api|worker|scheduler|bot
├── entrypoints/         процессы (composition roots): каждый берёт у модулей свою часть
│   ├── api.py           create_app(): middleware, роутеры модулей, обработчики ошибок, lifespan
│   ├── worker.py        outbox relay + консьюмеры (Kafka или локально)
│   ├── scheduler.py     задачи модулей по расписанию, под распределённой блокировкой
│   └── bot.py           aiogram: Telegram-роутеры модулей, Dishka в хендлерах
├── shared/              общее ядро: ничего не знает о модулях
│   ├── module.py        Module — что модуль отдаёт в сборку: провайдер, роутер, ошибки, подписки,
│   │                    консьюмеры, задачи, Telegram-роутер, startup
│   ├── domain/          EntityError, ForbiddenError, InvalidCredentialsError; ids.py (UserId);
│   │                    time.py (TimeService — всё про время, FrozenTime для тестов)
│   ├── application/     events.py (Event, IntegrationEvent), jobs.py (JobSpec), pagination.py, exceptions.py
│   │   └── ports/       UnitOfWork, IdentityProvider, Cache + DistributedLock, FileStorage,
│   │                    LlmClient, TelegramSender, PushSender
│   ├── infra/           реализации портов + фолбэки: cache.py (Redis), storage.py (S3), llm.py (Ollama),
│   │                    telegram.py, push.py (FCM), scheduler.py; messaging/ (шина, outbox,
│   │                    inbox, relay, Kafka); database/, config.py + di.py, logger.py, metrics.py
│   └── presentation/    http/ (middleware, ошибки, ops), telegram/ (общие команды /start, /help)
└── modules/
    ├── users/
    │   ├── api/         ПУБЛИЧНЫЙ контракт: contracts.py (UsersFacade, UserInfo, UserDeactivated…),
    │   │                http.py (UserReadResponse, правила полей); всё остальное в модуле приватно
    │   ├── domain/      entity.py, enums.py, errors.py
    │   ├── application/ interactors.py, facade.py (реализация UsersFacade), ports.py, dto.py, access.py
    │   ├── infra/       tables.py (таблица + mapping), gateway.py, password_hasher.py (argon2)
    │   ├── presentation/http/  router.py, schemas.py, errors.py (маппинг ошибок модуля)
    │   └── module.py    Dishka-провайдер модуля и users_module = Module(...)
    └── auth/            та же раскладка; зависит от users только через users.api,
                         реализует IdentityProvider и подписан на UserDeactivated

src/alembic.ini, src/alembic/   миграции; env.py импортирует bootstrap (все модули) и общую metadata;
                                ревизии — автогенерация или SQL (.up.sql / .down.sql)
```

### Правила

Их проверяет `tests/architecture/test_architecture.py`, так что CI упадёт, если их нарушить:

- **Модули общаются только через `api/`** другого модуля. Из `domain`/`application` — только
  через `api/contracts.py` (без фреймворков), из `presentation` — ещё и через `api/http.py`.
- **Без циклов** между модулями: `auth → users` можно, обратно — уже нельзя.
- **`shared` не импортирует модули.** Если ядру что-то нужно от модуля, ядро объявляет порт
  (как `IdentityProvider`), а модуль его реализует.
- **`module.py`** импортирует только composition root (`bootstrap.py`, `entrypoints/`, `run.py`).
- **Внешние библиотеки** (`aiokafka`, `redis`, `aiogram`, `aiobotocore`, `httpx`…) — только в
  `infra` и `presentation`; `domain` и `application` видят порты.
- **Слои внутри модуля и `shared`**:

| Слой | Можно импортировать |
|---|---|
| `domain` | stdlib, `domain` (свой и `shared`), `api/contracts` других модулей |
| `application` | то же + `application`; без фреймворков и `dishka` (DI — в `module.py`) |
| `infra` | всё, кроме `presentation` |
| `presentation` | всё, кроме composition root |

### Как модули взаимодействуют

| Нужно | Как | Пример |
|---|---|---|
| Спросить или попросить другой модуль | вызвать его фасад из `api/contracts.py` | `auth` → `UsersFacade.check_credentials()` |
| Сообщить, что что-то произошло | опубликовать событие; подписчики — в `Module.subscriptions` | `users` → `UserDeactivated` → `auth` удаляет сессии |
| Отреагировать позже и надёжно | `IntegrationEvent` + `Module.consumers` | `UserDeactivated` → outbox → worker |
| Делать что-то по расписанию | use case без аргументов + `Module.jobs` | `auth.cleanup_expired_refresh_tokens` раз в час |
| Отвечать в Telegram | aiogram `Router` в `Module.bot_router` | хендлер получает use case через `FromDishka` |
| Дать ядру возможность, которую реализует модуль | порт в `shared`, реализация в модуле | `IdentityProvider` ← `auth.TokenIdentityProvider` |

**Два вида подписки на событие.** `subscriptions` выполняются в том же запросе и той же
транзакции (`UnitOfWork` один на запрос), поэтому эффект атомарен. Если событие —
`IntegrationEvent` (у него есть `topic`), оно ещё и пишется в outbox в той же транзакции.
`worker` пересылает outbox в Kafka, а `consumers` модулей обрабатывают сообщение позже, каждый в
своей транзакции, не меньше одного раза. Inbox (`message_id`, обработчик) отсекает повторы, а
упавший после трёх попыток обработчик помечается `failed` и не блокирует поток. Без Kafka
`worker` отдаёт outbox своим консьюмерам сам, с теми же гарантиями. Обработчик выглядит
одинаково в обоих случаях, так что перенос реакции из синхронной в асинхронную — одна строка.

**Процессы.** Все четыре собирают один и тот же контейнер (`build_container()`), поэтому use case
одинаково вызывается из HTTP-роутера, Telegram-хендлера, консьюмера и задачи; у каждого вызова
свой REQUEST-скоуп (сессия, транзакция). Масштабирование: `api` — сколько угодно реплик;
`worker` — не больше числа партиций; `scheduler` — одна (лишняя безопасна: каждый запуск задачи
берёт блокировку, общую для реплик при заданном `REDIS_URL`); `bot` — ровно одна (polling).

Все модули пишут в одну БД. Таблицы у каждого модуля свои, чужие таблицы модуль не читает
(только через фасад). Внешний ключ `refresh_tokens.user_id → users.id` оставлен ради
целостности: это ссылка на уровне БД, а не Python-импорт между модулями.

## Добавить модуль

```bash
make module name=projects                 # или: uv run python scripts/new_module.py projects Project
make migration m="add projects"           # или make migration-sql m="add projects" — см. «Миграции»
make migrate
uv run pytest tests/api/test_projects_endpoints.py
```

Генератор создаёт `src/app/modules/projects/` со всеми слоями, `api/contracts.py` и `module.py`:
сущность `Project` (`title`, `description`, `owner_id`) и CRUD `/api/v1/projects`
(`GET`, `POST`, `GET/PATCH/DELETE /{id}`). Пользователь видит свои записи, админ — все
(проверка через `UsersFacade.is_admin`). Генерируется тест, модуль добавляется одной строкой в
`MODULES` (`bootstrap.py`), `docs/openapi.json` обновляется. Дальше вы переделываете сущность под
свою предметную область.

Ручной путь (если генератор не подходит) — повторите раскладку `modules/users/`:
1. `domain/`: сущность (dataclass) и ошибки (наследники `EntityError`).
2. `application/`: `ports.py`, `dto.py`, `interactors.py`.
3. `infra/`: `tables.py` (таблица на общей `metadata` + `map_once`), `gateway.py`.
4. `presentation/http/`: `schemas.py`, `router.py`, `errors.py` (`ErrorMap` модуля).
5. `api/contracts.py`: то, что можно другим модулям (фасад, DTO, события).
6. `module.py`: Dishka-провайдер и `Module(...)`; добавьте модуль в `MODULES` в `bootstrap.py`.

## Как писать код

**Интерактор** — класс с `__call__`; общие зависимости собраны в dataclass-контексте, и Dishka
передаёт их в конструктор (регистрация — в `module.py` модуля). Эндпоинт получает интерактор через `FromDishka[...]`, а текущего
пользователя — через `CurrentUserDep`, и передаёт `user.id` в интерактор. Команда в конце вызывает
`await self.uow.commit()`; запрос ничего не коммитит.

```python
@dataclass
class _UserContext:
    uow: UnitOfWork
    user_gateway: UserGateway
    ...

class CreateUser(_UserContext):
    async def __call__(self, user_id: UserId, data: UserCreateData) -> UserInfo:
        await require_admin(self.user_gateway, user_id)   # роль читается из БД -> 403
        user = User(email=data.email, ...)
        await self.uow.add(user)
        result = to_user_info(user)
        await self.uow.commit()                            # DuplicateError -> 409
        return result
```

**Транзакция** одна на HTTP-запрос: gateways и `UnitOfWork` всех модулей работают в одной
сессии. Без `commit()` изменения откатятся. Фасады других модулей не коммитят: коммитит интерактор,
который начал сценарий (так `auth` регистрирует пользователя и создаёт сессию одним коммитом).

**Ошибки**: интерактор бросает доменную ошибку (`raise ProjectNotFoundError`), а `ErrorMap`
модуля (`presentation/http/errors.py`) превращает её в API-ошибку (`NotFound`… из
`shared/presentation/http/errors/`) с нужным статусом и `code`. Общие ошибки (`ForbiddenError` → 403,
`InvalidCredentialsError` → 401) маппятся в `shared`. `DuplicateError` из `UnitOfWork.commit()` → 409,
прочие `ApplicationError` → 500 с записью в лог, ошибка без маппинга → 500 и `unmapped_domain_error`.

**Таблицы** описываются через `Table` в `infra/tables.py` модуля (на общей `metadata` из
`shared/infra/database/registry.py`) и привязываются к dataclass-сущностям через imperative mapping. В домене нет SQLAlchemy, а ORM всё равно отслеживает
изменения: изменили поле сущности, вызвали `commit()`, и изменение сохранилось.

**Миграции** бывают двух видов, и в одной цепочке их можно смешивать:

| | Автогенерация | SQL |
|---|---|---|
| Команда | `make migration m="..."` | `make migration-sql m="..."` |
| Источник | diff `tables.py` и БД | DDL, который пишете вы или экспортирует pgAdmin |
| Файлы | `xxxx_....py` с `op.create_table(...)` | `0003_x.py` (цепочка, не править) + `0003_x.up.sql` + `0003_x.down.sql` |

SQL-ревизия выполняет файл целиком в транзакции миграции: несколько команд, функции и триггеры с
`$$` допустимы. Готовый DDL удобно брать из pgAdmin: *Tools → Schema Diff* между dev-базой и
базой на текущем head даёт ALTER-скрипт (*Generate SQL* по таблице — это `CREATE`, он годится только
для новой таблицы). DDL из MySQL Workbench не подойдёт: другой диалект.

Домен от схемы не зависит, а `tables.py` остаётся: по нему SQLAlchemy сохраняет сущности и строит
запросы. Описывайте в нём колонки, которые нужны коду, и ограничения, на которые код
рассчитывает (`unique` → `DuplicateError`). Индексы, триггеры и партиции можно держать только в SQL.
CI делает `alembic check` на Postgres: если SQL и `tables.py` разошлись, сборка упадёт.

**Время** — только через `TimeService` (`shared/domain/time.py`): текущий момент (`now`, `after`,
`is_past`), приведение к UTC, формат API (`to_iso`), длительности из окружения (`parse_duration`).
Код, который решает по времени (сроки, расписания, JWT), получает `TimeService` из DI; поля
`created_at` по умолчанию берут `utc_now`. В тестах время подменяется: `make_app(time_provider(frozen))`,
дальше `frozen.advance(timedelta(days=31))` — пример в `tests/api/test_auth_endpoints.py`.

**Логи**: `logger.info("event_name", extra={...})`, где событие и его поля заранее перечислены в
`shared/infra/logger.py`. Свободный текст и данные запросов в лог не попадают.

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
Новые модули добавляют свои пути, это не нарушение. Выгрузка схемы для фронта:
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
| `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`, `KAFKA_GROUP_ID` | пусто — без Kafka | outbox → Kafka, консьюмеры читают топики |
| `WORKER_OUTBOX_POLL_INTERVAL`, `WORKER_OUTBOX_BATCH_SIZE` | `1.0`, `100` | relay |
| `REDIS_URL` | пусто — в памяти процесса | кеш и распределённые блокировки |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | пусто — `STORAGE_LOCAL_DIR` | файлы и presigned URL |
| `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, `OLLAMA_MAX_CONCURRENCY` | пусто — 503 на вызовы LLM | локальная LLM |
| `TELEGRAM_BOT_TOKEN` | пусто — сообщения только в лог | бот и исходящие сообщения |
| `FCM_SERVICE_ACCOUNT_FILE` | пусто — push только в лог | push в мобильное приложение |
| `MOBILE_MIN_APP_VERSION` | пусто — без проверки | ниже — 426 `APP_UPDATE_REQUIRED` |

Каждая группа — свой Pydantic-конфиг в `shared/infra/config.py`. Новому модулю нужен конфиг?
Добавьте класс в `config.py` и в кортеж `CONFIGS` в `shared/infra/di.py`.

Недоступная внешняя система бросает `ServiceUnavailableError`, и API отвечает 503
`SERVICE_UNAVAILABLE`; остальное приложение продолжает работать. `/health/readiness` проверяет
только БД, чтобы падение LLM или брокера не снимало API с балансировщика.

## Тесты

```bash
make test                                                          # SQLite in-memory, без Docker
make test-pg DB=postgresql+asyncpg://postgres:postgres@localhost/app_test   # отдельная БД!
make check                                                         # ruff + mypy + тесты
```

- `tests/api/` — HTTP-сценарии через `TestClient` (фикстуры `client`, `admin_headers`, `register_user`);
  БД подменяется через Dishka-провайдер с `override=True`;
- `tests/unit/` — интеракторы на фейках портов и шины событий, без БД;
- `tests/infra/` — outbox → relay → консьюмеры и inbox на тестовой БД, SQL-миграции (offline),
  планировщик, адаптеры
  (Ollama и FCM на `httpx.MockTransport`, локальное хранилище), точки входа, 426 и 503;
- `tests/architecture/` — границы модулей, отсутствие циклов, слои и актуальность `docs/openapi.json`;
- `tests/contract/` — OpenAPI совпадает с FastAPI-Fish.

Для `TEST_DB_URL` используйте отдельную базу: тесты удаляют таблицы после каждого прогона.
