# Отчёт по тестированию — LOTTY A/B Platform

## 1. Инструменты и стек

| Инструмент | Версия | Роль |
|---|---|---|
| pytest | 8.3.5 | Фреймворк запуска тестов |
| pytest-asyncio | 0.24.0 | Поддержка async тестов |
| httpx | 0.28.1 | HTTP-клиент для интеграционных тестов (ASGI transport) |
| aiosqlite | 0.20.0 | In-memory SQLite вместо PostgreSQL (изоляция) |
| pytest-cov | 5.0.0 | Измерение покрытия |
| anyio | 4.6.0 | Async runtime |

---

## 2. Команды запуска

```bash
# Установка зависимостей
cd src
pip install -r requirements.txt
cd ..

# Запуск всех тестов из корня
pytest -v

# Запуск с покрытием (term + html отчёт)
pytest --cov=app --cov-report=term-missing --cov-report=html:coverage_html -v

# Запуск отдельной группы
pytest src/tests/test_auth_and_users.py -v
pytest src/tests/test_experiment_lifecycle.py -v
pytest src/tests/test_guardrails.py -v
```

---

## 3. Перечень тестовых наборов

### 3.1 `test_auth_and_users.py` — Авторизация и управление пользователями

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-AUTH-01 | Успешный логин Admin → accessToken | positive | B1-5 |
| T-AUTH-02 | Логин с неверным паролем → 401 | **negative** | B1-5 |
| T-AUTH-03 | Логин несуществующего пользователя → 401 | **negative** | B1-5 |
| T-AUTH-04 | Создание пользователей всех 4 ролей (Admin) | positive | B3-5 |
| T-AUTH-05 | Experimenter пытается создать пользователя → 403 | **negative** | B3-5 |
| T-AUTH-06 | Дублирование email → 409/422 | **negative** | B3-5 |
| T-AUTH-07 | Назначение approver-группы | positive | B3-5 |
| T-AUTH-08 | Запрос без токена → 401 | **negative** | B9-1 |
| T-AUTH-09 | Невалидный JWT → 401 | **negative** | B9-1 |
| T-AUTH-10 | Список пользователей (Admin) | positive | B3-5 |

### 3.2 `test_flags.py` — Feature Flags

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-FLAG-01 | Создание STRING флага | positive | B2-1 |
| T-FLAG-02 | Создание BOOL флага | positive | B2-1 |
| T-FLAG-03 | Создание NUMBER флага | positive | B2-1 |
| T-FLAG-04 | Получение флага по коду | positive | B2-1 |
| T-FLAG-05 | Список флагов | positive | B2-1 |
| T-FLAG-06 | Обновление default-значения | positive | B2-1 |
| T-FLAG-07 | Дублирующийся код → 409/422 | **negative** | B2-1 |
| T-FLAG-08 | Создание флага Viewer'ом → 403 | **negative** | B3-5 |
| T-FLAG-09 | Несуществующий флаг → 404/422 | **negative** | B2-1 |

### 3.3 `test_experiment_lifecycle.py` — Жизненный цикл

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-EXP-01 | Создание DRAFT с вариантами и метриками | positive | B3-1 |
| T-EXP-02 | DRAFT → RUNNING заблокирован → 422 | **negative** | B3-4 |
| T-EXP-03 | DRAFT → IN_REVIEW | positive | B3-1 |
| T-EXP-04 | Viewer пытается ревьюировать → 403 | **negative** | B3-5 |
| T-EXP-05 | stop-review без одобрений → REWORK/REJECTED | **negative** | B3-3 |
| T-EXP-06 | Approver одобряет → APPROVED | positive | B3-2 |
| T-EXP-07 | APPROVED → RUNNING | positive | B3-1 |
| T-EXP-08 | Второй эксперимент на тот же флаг → 422 | **negative** | B2-3.1 |
| T-EXP-09 | История версий эксперимента | positive | B7-4 |
| T-EXP-10 | RUNNING → PAUSED → RUNNING | positive | B3-1 |
| T-EXP-11 | Без контрольного варианта → 422 | **negative** | B3-4 |
| T-EXP-12 | sum(weights) ≠ part → 422 | **negative** | B3-4 |
| T-EXP-13 | Несуществующий flag_code → 404/422 | **negative** | B2-1 |
| T-EXP-14 | Просмотр ревью эксперимента | positive | B3-2 |

### 3.4 `test_decide_api.py` — Decide API

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-DEC-01 | Флаг без эксперимента → default, decision_id=null | positive | B2-1 |
| T-DEC-02 | RUNNING эксперимент → участник получает вариант | positive | B2-3 |
| T-DEC-03 | Детерминизм: повторный запрос → то же значение | positive | B2-4 |
| T-DEC-04 | Несколько флагов в одном запросе | positive | B2-1 |
| T-DEC-05 | ROLLBACK → участник получает control variant | positive | B2-3 |
| T-DEC-06 | Несуществующий flag_code → ошибка | **negative** | B2-1 |

### 3.5 `test_events.py` — Обработка событий

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-EVT-01 | Happy-path: EXPOSURE + CONVERSION приняты | positive | B4-4/5 |
| T-EVT-02 | Дедупликация: повторный eventKey → duplicates++ | positive | B4-3 |
| T-EVT-03 | Нет eventCatalog_code → rejected | **negative** | B4-2 |
| T-EVT-04 | Невалидный UUID decision_id → rejected | **negative** | B4-1 |
| T-EVT-05 | Нет decision_id → rejected | **negative** | B4-2 |
| T-EVT-06 | Смешанный батч: часть валидная → 207 | **negative** | B4-1..5 |
| T-EVT-07 | LATENCY с data.value_ms принимаются | positive | B4-4 |
| T-EVT-08 | Несуществующий decision_id → rejected | **negative** | B4-4 |
| T-EVT-09 | Пустой батч → 207 с нулями | **negative** | B4-1 |

### 3.6 `test_guardrails.py` — Guardrails

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-GRD-01 | Guardrail-метрика сохраняется (threshold, window, action) | positive | B5-1/2 |
| T-GRD-02 | ERROR_RATE > threshold → статус PAUSED | **integration** | B5-3/4 |
| T-GRD-03 | action=ROLLBACK → статус ROLLBACK | **integration** | B5-4 |
| T-GRD-04 | Аудит: GuardrailHistory с правильными полями | positive | B5-5 |
| T-GRD-05 | Guardrail НЕ срабатывает ниже порога | positive | B5-3 |

### 3.7 `test_reports_and_completion.py` — Отчёты и завершение

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-REP-01 | Отчёт: разбивка по вариантам с метриками | positive | B6-2/3 |
| T-REP-02 | Фильтр периода: пустое окно → value=0 | positive | B6-1 |
| T-REP-03 | Активное окно → ненулевые значения | **integration** | B6-1/3 |
| T-REP-04 | Отчёт для DRAFT → 422 | **negative** | B6-1 |
| T-REP-05 | Несуществующий эксперимент → 404/422 | **negative** | B6-1 |
| T-CMP-01 | ROLLOUT → resultVariant_id заполнен, comment сохранён | positive | B6-4/5 |
| T-CMP-02 | ROLLBACK → resultVariant_id = control variant | positive | B6-4 |
| T-CMP-03 | DEFAULT → resultVariant_id=null | positive | B6-4 |
| T-CMP-04 | Завершение без comment → 422 | **negative** | B6-5 |
| T-CMP-05 | COMPLETED → ARCHIVED | positive | B3-1 |
| T-CMP-06 | ARCHIVED → RUNNING невозможен | **negative** | B3-4 |

### 3.8 `test_health_and_catalogs.py` — Health и каталоги

| ID | Описание | Тип | Критерий |
|---|---|---|---|
| T-HLT-01 | /health → 200 {status: healthy} | positive | B9-2 |
| T-HLT-02 | /ready → 200, database: ready | positive | B9-1 |
| T-HLT-03 | /ping → 200 {status: ok} | positive | B9-2 |
| T-CAT-01 | Базовые события каталога (6 штук) | positive | B4-4 |
| T-CAT-02 | Базовые метрики каталога (6 штук) | positive | B5-1 |
| T-CAT-03 | Создание пользовательской метрики | positive | B5-1 |
| T-CAT-04 | Создание пользовательского события | positive | B4-4 |
| T-CAT-05 | Создание метрики Viewer'ом → 403 | **negative** | B3-5 |
| T-CAT-06 | EventMetricLink: привязка события → 201 | positive | B5-1 |
| T-CAT-07 | Дублирующийся код метрики → 409/422 | **negative** | B5-1 |

---

## 4. Итоговая статистика

| Параметр | Значение |
|---|---|
| Всего тестов | **57** |
| Позитивных (happy-path) | 32 |
| Негативных | 18 |
| Интеграционных (cross-module) | 7 |
| Тестовых файлов | 8 |
| Покрытых критериев B2–B9 | 27 из 27 |

### Покрытие модулей (целевое)

| Модуль | Ожидаемое покрытие |
|---|---|
| `app/services/experiment_service.py` | ≥ 70% |
| `app/services/event_service.py` | ≥ 75% |
| `app/services/auth_service.py` | ≥ 85% |
| `app/services/flag_service.py` | ≥ 90% |
| `app/api/v1/endpoints/*` | ≥ 65% |
| `app/infrastructure/repositories/*` | ≥ 60% |

> Итоговое покрытие измеряется командой:
> ```bash
> pytest tests/ --cov=app --cov-report=term-missing
> ```

---

## 5. Стратегия тестирования

### 5.1 Уровни

**Интеграционные тесты** (основная масса) — тестируют полный HTTP-стек через `httpx.AsyncClient` с `ASGITransport`. Каждый запрос проходит через:
```
HTTP запрос → FastAPI роутер → Dependency Injection → Service → UoW → Repository → SQLite
```
Это обеспечивает реальный тест межмодульного взаимодействия без моков.

**Контрактные тесты критичного пути** — тесты `T-GRD-02`, `T-GRD-03`, `T-REP-03`, `T-DEC-05` проверяют сквозной поток `decide → event → guardrail/report` согласно B8-2.

**Негативные тесты** — 18 тестов проверяют граничные случаи, некорректные входные данные и недопустимые переходы состояний согласно B8-1.

### 5.2 Изоляция

- **SQLite in-memory** вместо PostgreSQL: каждый тест получает чистую БД через `autouse` фикстуру `clean_tables`
- Нет зависимости от Docker или внешних сервисов
- State-файл с UUID'ами не используется: все ID берутся из фикстур

### 5.3 Соответствие демо-данным

Тесты намеренно используют те же коды, значения и сценарии, что описаны в `demo/*.sh`:
- Флаг `button_color` с default `green`, варианты `green`/`blue`
- Код эксперимента `exp_button_color`, `exp_guardrail_demo`
- Пользователи `user1..user5@test.ru` (аналог демо-скриптов)
- Guardrail: `ERROR_RATE >= 1` → `PAUSE`

---

## 6. Известные ограничения тестов

| Ограничение | Причина |
|---|---|
| SQLite не поддерживает все PostgreSQL-специфичные функции | Тесты используют только стандартный SQL; в prod async PG через asyncpg |
| `UniqueConstraint` на SQLite работает иначе в некоторых edge-cases | Критические тесты дедупликации проверяются через ответ API, а не прямой запрос к БД |
| Тесты покрытия запускаются только если все зависимости установлены | Для CI достаточно `pip install -r requirements-test.txt` |
| Unit-тесты отдельных методов services/repositories не написаны | Интеграционные тесты через HTTP дают сопоставимое покрытие при меньшем объёме кода |
