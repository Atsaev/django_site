# atsaev-dev.ru

Личный сайт-портфолио на Django: витрина проектов, блог и резюме с генерацией PDF. Сделан как демонстрационный проект для поиска работы Python-разработчиком — с продакшн-деплоем через CI/CD (GitHub Actions → GHCR), а не просто локальным тудулистом.

**Live:** [atsaev-dev.ru](https://atsaev-dev.ru)

## Стек

- **Backend:** Django 6.1, Python 3.12
- **Зависимости:** uv (`pyproject.toml` / `uv.lock`)
- **База данных:** PostgreSQL 17 (psycopg 3)
- **WSGI-сервер:** Granian
- **Статика:** WhiteNoise (collectstatic выполняется на этапе сборки образа)
- **Редактор контента:** django-ckeditor-5
- **Обработка изображений:** django-imagekit + Pillow
- **Генерация PDF:** WeasyPrint (HTML→PDF, Pango)
- **Контейнеризация:** Docker, Docker Compose
- **CI/CD:** GitHub Actions — сборка и публикация образа в GitHub Container Registry
- **Прокси / TLS:** Caddy
- **Фронтенд:** Bootstrap 5, кастомный CSS в терминальной эстетике, ванильный JS

## Возможности

- **Портфолио** — карточки проектов с обложками, стеком технологий, ссылками на демо и GitHub
- **Блог** — посты с WYSIWYG-редактором (CKEditor 5), тегами, счётчиком просмотров
- **Резюме** — полностью редактируется через админку (профиль, опыт работы, навыки по категориям, образование, языки), с кнопкой скачивания в PDF
- **Единая админка** — весь контент сайта управляется через стандартную Django Admin, без написания собственной CMS
- **Демо-эндпоинты** — отдельные live-проекты (AI Security) задеплоены на том же сервере и упомянуты в резюме и портфолио

## Структура проекта

```
.
├── .github/workflows/   # CI/CD: сборка Docker-образа и публикация в GHCR
├── config/              # настройки Django, корневой urls.py
├── portfolio/           # главная страница, модель Project
├── blog/                # посты блога, модель Post
├── resume/              # резюме: Profile, Experience, Skill, Education, Language
├── templates/           # общие шаблоны (base.html, navbar, footer)
├── static/              # CSS, JS
├── media/               # загруженные пользователем файлы (в git не хранятся)
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── manage.py
```

## Локальный запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Atsaev/django_site.git
cd django_site
```

### 2. Установить зависимости (uv)

```bash
uv sync
```

На macOS для генерации PDF (WeasyPrint) нужен Pango:

```bash
brew install pango
```

В Docker-образе Pango ставится автоматически через apt — отдельно ничего делать не нужно.

### 3. Поднять PostgreSQL

```bash
docker run --name portfolio-pg \
  -e POSTGRES_DB=portfolio_db \
  -e POSTGRES_USER=portfolio_user \
  -e POSTGRES_PASSWORD=changeme \
  -p 5433:5432 \
  -d postgres:17-alpine
```

### 4. Настроить `.env`

```
DEBUG=True
SECRET_KEY=django-insecure-замени-на-свой
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=portfolio_db
DB_USER=portfolio_user
DB_PASSWORD=changeme
DB_HOST=localhost
DB_PORT=5433
```

### 5. Миграции и суперпользователь

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

### 6. Заполнить контентом (опционально, но рекомендуется)

```bash
uv run python manage.py seed_resume
uv run python manage.py seed_projects
```

### 7. Запустить

```bash
uv run python manage.py runserver
```

Сайт откроется на `http://127.0.0.1:8000/`, админка — на `/admin/`.

## Деплой

### CI/CD через GitHub Actions

Workflow `.github/workflows/deploy.yml` срабатывает при пуше в ветку `main`:

1. Собирает Docker-образ из `Dockerfile` (установка зависимостей через uv, Pango для WeasyPrint, `collectstatic`)
2. Публикует образ в GitHub Container Registry: `ghcr.io/atsaev/portfolio-site:latest`

### Запуск на сервере (Docker Compose)

После того как Actions собрал и опубликовал образ, `~/projects/portfolio/docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:17-alpine
    container_name: atsaev-portfolio-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    image: ghcr.io/atsaev/portfolio-site:latest
    container_name: atsaev-portfolio-web
    restart: unless-stopped
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    networks:
      - app-network

networks:
  app-network:
    external: true

volumes:
  pgdata:
  static_volume:
  media_volume:
```

Имя контейнера (`atsaev-portfolio-web`) должно совпадать с адресом в `reverse_proxy` у Caddy. Порт наружу не публикуется — Caddy ходит до контейнера по docker-сети. Статику отдаёт WhiteNoise, порт 8000 слушает Granian.

> **Замечание про `static_volume`:** собранная статика (`collectstatic`) уже лежит в образе в `/app/staticfiles`, поэтому монтировать `static_volume:/app/staticfiles` необязательно — и даже вредно: том живёт дольше образа, и после обновлений отдаётся старая статика (с включённым WhiteNoise-манифестом это особенно заметно — новые файлы с новыми хешами в том не попадают). Надёжнее убрать этот том из compose; если он нужен, после каждого обновления образа обновляйте его вручную: `docker compose exec web uv run python manage.py collectstatic --noinput`.

```bash
cd ~/projects/portfolio
docker compose up -d --pull always
```

### Первоначальная настройка (миграции, контент)

```bash
docker exec -it atsaev-portfolio-web uv run python manage.py migrate
docker exec -it atsaev-portfolio-web uv run python manage.py createsuperuser
docker exec -it atsaev-portfolio-web uv run python manage.py seed_resume
docker exec -it atsaev-portfolio-web uv run python manage.py seed_projects
```

### TLS и проксирование (Caddy)

TLS терминирует Caddy, запросы проксируются на контейнер портфолио по имени в общей docker-сети:

```
atsaev-dev.ru {
    handle /cve/* {
        uri strip_prefix /cve
        reverse_proxy projects-cve-agent-1:8000
    }

    handle /fuzzer/* {
        uri strip_prefix /fuzzer
        reverse_proxy projects-smart-fuzzer-1:8000
    }

    handle_path /media/* {
        root * /srv/atsaev/media
        file_server
    }

    handle {
        reverse_proxy atsaev-portfolio-web:8000
    }

    encode gzip
}
```

Блок `handle /media/*` обязателен: в проде Django медиафайлы не отдаёт (WhiteNoise обслуживает только статику), поэтому загруженные через админку фото и картинки CKEditor'а раздаёт Caddy напрямую из смонтированного тома.

Caddy работает в контейнере — в его `docker-compose.yml` нужно смонтировать тот же media-том, что и у портфолио:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
      - portfolio_media_volume:/srv/atsaev/media:ro
    networks:
      - app-network

networks:
  app-network:
    external: true

volumes:
  caddy_data:
  caddy_config:
  portfolio_media_volume:
    external: true
```

Точное имя тома зависит от имени compose-проекта: проверь
`docker volume ls | grep media` (для папки `~/projects/portfolio` — `portfolio_media_volume`). Оба стека должны быть в одной docker-сети `app-network` (создать один раз: `docker network create app-network`).

## Management-команды

| Команда       | Назначение |
|---------------|------------|
| `seed_resume` | Заполняет резюме реальными данными (профиль, опыт, навыки, образование, языки)|
| `seed_projects` | Заполняет портфолио проектами |

Обе идемпотентны — можно запускать повторно, старые записи заменяются новыми.

## Автор

**Ацаев Хасан** — Python-разработчик, фокус на backend и AI Security.

- GitHub: [github.com/Atsaev](https://github.com/Atsaev)
- Telegram: [@atsayev](https://t.me/atsayev)
- Email: atsaev.khasan@yandex.ru
