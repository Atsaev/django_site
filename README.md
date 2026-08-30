# atsaev-dev.ru

Личный сайт-портфолио на Django: витрина проектов, блог и резюме с генерацией PDF. Сделан как демонстрационный проект для поиска работы Python-разработчиком — с продакшн-деплоем, а не просто локальным тудулистом.

**Live:** [atsaev-dev.ru](https://atsaev-dev.ru)

## Стек

- **Backend:** Django 6.1
- **База данных:** PostgreSQL 17 (alpine)
- **WSGI-сервер:** Granian
- **Редактор контента:** django-ckeditor-5
- **Обработка изображений:** django-imagekit + Pillow
- **Генерация PDF:** Playwright (headless Chromium)
- **Контейнеризация:** Docker, Docker Compose
- **Прокси / TLS:** Nginx, Let's Encrypt (certbot)
- **Фронтенд:** Bootstrap 5, кастомный CSS в терминальной эстетике, ванильный JS

## Возможности

- **Портфолио** — карточки проектов с обложками, стеком технологий, ссылками на демо и GitHub
- **Блог** — посты с WYSIWYG-редактором (CKEditor 5), тегами, счётчиком просмотров
- **Резюме** — полностью редактируется через админку (профиль, опыт работы, навыки по категориям, образование, языки), с кнопкой скачивания в PDF
- **Единая админка** — весь контент сайта управляется через стандартную Django Admin, без написания собственной CMS
- **Демо-эндпоинты** — три отдельных live-проекта (AI Security) задеплоены на поддоменах и упомянуты в резюме и портфолио

## Структура проекта

```
.
├── config/          # настройки Django, корневой urls.py
├── portfolio/        # главная страница, модель Project
├── blog/             # посты блога, модель Post
├── resume/            # резюме: Profile, Experience, Skill, Education, Language
├── templates/         # общие шаблоны (base.html, navbar, footer)
├── static/            # CSS, JS
├── nginx/             # конфиг Nginx для продакшна
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Локальный запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Atsaev/django_site.git
cd django_site
```

### 2. Создать виртуальное окружение и поставить зависимости

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

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
python manage.py migrate
python manage.py createsuperuser
```

### 6. Заполнить контентом (опционально, но рекомендуется)

```bash
python manage.py seed_resume
python manage.py seed_projects
```

### 7. Запустить

```bash
python manage.py runserver
```

Сайт откроется на `http://127.0.0.1:8000/`, админка — на `/admin/`.

## Деплой через Docker

```bash
docker compose up -d db web
docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d atsaev-dev.ru -d www.atsaev-dev.ru
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_resume
docker compose exec web python manage.py seed_projects
```

Nginx поднимается вместе с остальными сервисами и терминирует TLS, проксируя запросы на Django через Granian.

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
