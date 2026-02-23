# SPEC.md — Link Shortener Service (Claude Code)

## 0) Цель
Сервис сокращения ссылок с управлением и аналитикой: создание коротких кодов, редирект, CRUD для владельца, поиск по original_url, TTL с авто-удалением, статистика, кэширование популярных переходов.

## 1) Принципы разработки
- DDD + Clean Architecture: слои `presentation` → `application` → `domain` → `infrastructure`.
- Минимизация контекста для LLM:
  - Каждый файл ≤ 200 строк, одна ответственность.
  - Никаких “магических” зависимостей: явные интерфейсы, явные DTO/команды.
  - Единый словарь доменных терминов (см. раздел 3).
  - Любая логика — в `domain`/`application`, инфраструктура только адаптеры.
- Чистый код, без комментариев.
- Работа с PostgreSQL через SQLAlchemy только через Repository + Unit of Work. Прямых запросов из application/presentation нет.

## 2) Технологический стек
- API: FastAPI (HTTP JSON), Pydantic для DTO.
- DB: PostgreSQL + SQLAlchemy 2.x (async).
- Cache: Redis (async клиент).
- Migrations: Alembic.
- Background jobs: APScheduler или Celery (выбрать один) для удаления истёкших ссылок и опциональных политик очистки.
- Auth: JWT (access token), bcrypt/argon2 для хэширования паролей.

## 3) Домен и язык (Ubiquitous Language)
- User: зарегистрированный пользователь.
- Link: сущность короткой ссылки.
- ShortCode: короткий код (генерируемый).
- Alias: кастомный short_code, задаваемый пользователем.
- OriginalUrl: исходный URL.
- ExpiresAt: время истечения (точность до минуты).
- Click: переход по ссылке (учёт в статистике).
- Stats: агрегированная статистика по Link.

## 4) Доменные сущности и инварианты
### 4.1 User
- `id: UUID`
- `email: str` (уникальный)
- `password_hash: str`
- `created_at: datetime`

### 4.2 Link
- `id: UUID`
- `short_code: str` (уникальный)
- `original_url: str`
- `created_at: datetime`
- `updated_at: datetime`
- `expires_at: datetime | None`
- `owner_user_id: UUID | None` (null = создано гостем)
- `is_deleted: bool` (soft delete для истории / опционально)
- Инварианты:
  - `short_code` уникален.
  - Если задан `expires_at`, то `expires_at` округлён/валидирован до минут.
  - `original_url` валиден (scheme http/https).
  - Истёкшая ссылка недоступна для редиректа и должна быть удалена/помечена как удалённая.

### 4.3 LinkStats (агрегат/проекция)
- `link_id: UUID`
- `clicks: int`
- `last_used_at: datetime | None`
- Источник истины: DB. Кэш может ускорять редирект, но статистика фиксируется в DB.

## 5) Use Cases (Application Layer)
Каждый use case — отдельный класс/функция в `application/use_cases/*`:
- `ShortenLink`
  - вход: `original_url`, `custom_alias?`, `expires_at?`, `actor_user_id?`
  - выход: `short_code`, `original_url`, `expires_at`, `created_at`
  - правила: проверка уникальности alias/кода, валидация URL, сохранение владельца (или null), запись Link + LinkStats.
- `ResolveLinkRedirect`
  - вход: `short_code`
  - выход: `original_url` (для редиректа)
  - побочные эффекты: инкремент кликов, обновление `last_used_at`, кеширование.
- `GetLinkInfo`
  - вход: `short_code`
  - выход: данные Link (без редиректа)
- `UpdateLink`
  - доступ только владельцу (owner_user_id == actor_user_id)
  - стратегия по умолчанию: обновляем `original_url` (или допускаем смену `short_code` как вариант реализации, но строго уникально)
  - очищаем кэш
- `DeleteLink`
  - доступ только владельцу
  - очищаем кэш
- `GetLinkStats`
  - вход: `short_code`
  - выход: `original_url`, `created_at`, `clicks`, `last_used_at`, `expires_at`
- `SearchLinkByOriginalUrl`
  - вход: `original_url`
  - выход: список ссылок (ограничить пагинацией)
- `RegisterUser`
  - вход: `email`, `password`
  - выход: `user_id`
- `LoginUser`
  - вход: `email`, `password`
  - выход: `access_token`
- `PurgeExpiredLinks`
  - периодическая задача
  - действие: удалить/пометить истёкшие ссылки, очистить кэш

## 6) Публичное API (Presentation Layer)
### Auth
- `POST /auth/register`
- `POST /auth/login`

### Links

Создание:
- `POST /links/shorten`
Redirect:
- `GET /opupupa/{short_code}`
Информация:
- `GET /links/{short_code}`
Обновление:
- `PUT /links/{short_code}` (auth + owner)
Удаление:
- `DELETE /links/{short_code}` (auth + owner)
Статистика:
- `GET /links/{short_code}/stats`
Поиск:
- `GET /links/search?original_url={url}&page=&size=`

Ошибки:
- 400: невалидный URL/дата
- 401: неавторизован
- 403: не владелец
- 404: не найдено/истекло
- 409: alias/code занят

## 7) Репозитории и UoW (Infrastructure ↔ Domain)
### 7.1 Интерфейсы (domain/application boundary)
- `IUserRepository`
  - `get_by_email(email)`
  - `get_by_id(id)`
  - `add(user)`
- `ILinkRepository`
  - `get_by_short_code(code)`
  - `get_by_id(id)`
  - `find_by_original_url(url, paging)`
  - `exists_short_code(code)`
  - `add(link)`
  - `update(link)`
  - `delete(link)` (soft/hard по реализации)
  - `list_expired(now, limit)`
- `ILinkStatsRepository`
  - `get_by_link_id(link_id)`
  - `add(stats)`
  - `increment_click(link_id, used_at)`
- `IUnitOfWork`
  - `users`, `links`, `stats`
  - `commit()`, `rollback()`

### 7.2 Реализация
- `SqlAlchemyUnitOfWork` управляет транзакцией async session.
- Репозитории используют только session из UoW.
- Модели SQLAlchemy находятся в `infrastructure/db/models`, маппинг в домен через фабрики/мапперы.

## 8) Кэширование (Redis)
Цели: ускорить `GET /{short_code}` и популярные ссылки.
- Ключи:
  - `link:code:{short_code}` → `{original_url, expires_at, link_id}`
  - `link:popular` (опционально ZSET для топ ссылок)
- Политика:
  - При resolve:
    - сначала Redis, при miss — DB, затем set в Redis с TTL:
      - если `expires_at` задан → TTL = expires_at - now
      - иначе TTL по умолчанию (например 24h)
  - При update/delete/purge: удалить `link:code:{short_code}`
  - Популярность: инкремент в ZSET на resolve (опционально)

Статистика:
- Фиксируется в DB транзакционно.
- Допускается буферизация кликов в Redis с периодическим сбросом, но только если не усложняет MVP. По умолчанию сразу в DB.

## 9) Авто-удаление истёкших ссылок
- Периодическая задача `PurgeExpiredLinks` каждые 1–5 минут.
- Истёкшие:
  - либо hard delete Link + Stats
  - либо soft delete (для “истории истёкших”) + отдельный read endpoint (доп. фича)
- При удалении: очистка кэша по `short_code`.

## 10) Структура проекта
- `src/`
  - `presentation/`
    - `api/routers/` (auth, links, redirect)
    - `api/deps/` (auth dependency, uow provider)
    - `schemas/` (Pydantic request/response)
  - `application/`
    - `use_cases/`
    - `dto/`
    - `services/` (short_code generator, time provider)
    - `errors/`
  - `domain/`
    - `entities/` (User, Link, LinkStats)
    - `value_objects/` (ShortCode, OriginalUrl, ExpiresAt)
    - `repositories/` (interfaces)
  - `infrastructure/`
    - `db/` (engine, session, models, alembic)
    - `repositories/` (sqlalchemy implementations)
    - `cache/` (redis client + cache adapter)
    - `auth/` (jwt, password hasher)
    - `jobs/` (scheduler/celery tasks)
- `tests/` (unit: domain/application, integration: api/db/redis)

## 11) Генерация short_code
- Base62 (A–Z a–z 0–9), длина по умолчанию 7–10.
- Коллизии решаются повторной генерацией с проверкой `exists_short_code`.
- Для `custom_alias` — только проверка уникальности и валидация формата (allowed charset, min/max length).

## 12) Конфигурация
ENV:
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `JWT_EXPIRES_MIN`
- `BASE_URL`
- `SHORT_LINK_PREFIX=opupupa`
- `DEFAULT_CACHE_TTL_SEC`
- `PURGE_INTERVAL_SEC`

Полный формат короткой ссылки:
{BASE_URL}/{SHORT_LINK_PREFIX}/{short_code}
Пример:
https://example.com/opupupa/a8Gh12K

## 13) Acceptance Criteria (MVP)
- Все обязательные endpoints работают согласно правилам доступа.
- CRUD update/delete только для владельца (JWT).
- Статистика: clicks и last_used_at корректно обновляются при редиректе.
- TTL: истёкшие ссылки недоступны, авто-удаляются задачей.
- Redis кэш используется минимум для редиректа, с инвалидацией на update/delete/purge.
- SQLAlchemy используется только внутри репозиториев под UoW.
- Код без комментариев, слой домена не зависит от FastAPI/SQLAlchemy/Redis.
