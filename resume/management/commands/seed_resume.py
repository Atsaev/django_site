from django.core.management.base import BaseCommand

from resume.models import (
    EducationItem,
    Experience,
    Language,
    Profile,
    Skill,
    SkillCategory,
)


class Command(BaseCommand):
    help = "Заполняет резюме реальными данными"

    def handle(self, *args, **options):
        Profile.objects.update_or_create(
            pk=1,
            defaults=dict(
                name="Ацаев Хасан",
                role="Python-разработчик",
                location="Москва",
                employment_status="open_to_work",
                about=(
                    "<p>После пяти лет в B2B-продажах и рекламе я поймал себя на мысли, что меня "
                    "больше драйвит не закрытие квартального плана, а поиск элегантного технического "
                    "решения. Сейчас применяю ту же системность, но к архитектуре кода, CI/CD и "
                    "мультиагентным системам.</p>"
                    "<p>За плечами 600+ часов практики в Яндекс Практикуме, собственные проекты "
                    "задеплоены на реальный сервер. Строю архитектуру с нуля: тесты, CI/CD, Docker, деплой.</p>"
                    "<p>Цель — не просто писать код, а строить защищённые backend-решения на стыке "
                    "AI Security и мультиагентных систем.</p>"
                    "<p><strong>Изучаю сейчас:</strong> «Designing Data-Intensive Applications» "
                    "(M. Kleppmann), «Security Engineering» (R. Anderson), «Multiagent Systems» "
                    "(Shoham, Leyton-Brown); курсы Stepik по Django+Docker и продвинутому FastAPI.</p>"
                ),
                email="atsaev.khasan@yandex.ru",
                telegram="atsayev",
                github="github.com/Atsaev",
            ),
        )

        Experience.objects.all().delete()
        experiences = [
            dict(
                company="Яндекс",
                position="Python-разработчик (Контрибьютор)",
                location="Москва",
                period_text="Фев 2026 — сейчас · 7 мес",
                start_date="2026-02-01",
                is_dev_role=True,
                order=1,
                tech_stack="Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL",
                description=(
                    "<p>Backend-разработка модуля бронирования для системы управления кафе.</p><ul>"
                    "<li>Онлайн-резервирование столов с проверкой конфликтов и ролевой фильтрацией — "
                    "снижает ручную работу администратора до 40%.</li>"
                    "<li>BaseRepository с Soft Delete; оптимизация через joinedload — 2.5с → 200мс.</li>"
                    "<li>Pydantic v2-схемы с кастомными валидаторами — меньше багов в проде.</li>"
                    "<li>Архитектура Repository → Service → Router, покрытие тестами.</li></ul>"
                ),
            ),
            dict(
                company="Проектная деятельность",
                position="Python-разработчик",
                location="",
                period_text="Мар 2025 — сейчас · 1 год 6 мес",
                start_date="2025-03-01",
                is_dev_role=True,
                order=2,
                tech_stack="LangGraph, DeepSeek, FastAPI, Docker, GitHub Actions, Whisper, Ollama",
                description=(
                    "<p><strong>CVE Agent</strong> — мультиагентная система анализа уязвимостей "
                    "(Analyst → Risk → Mitigation → Reporter). Сократил разбор CVE с ~30 до 2–3 минут.</p>"
                    "<p><strong>Smart Fuzzer</strong> — LLM-генерация тест-кейсов для поиска уязвимостей "
                    "в Python-коде.</p>"
                    "<p><strong>Foodgram</strong> — продакшн-сервис с CI/CD через GitHub Actions.</p>"
                    "<p><strong>Security Pipeline</strong> — автосбор данных об уязвимостях из NVD API.</p>"
                    "<p><strong>Sales Assistant</strong> — real-time транскрипция звонков (Whisper) + "
                    "локальная LLM (Ollama) без отправки данных наружу.</p>"
                ),
            ),
            dict(
                company="Т-Банк",
                position="Ведущий менеджер по работе со средним бизнесом",
                location="Москва",
                period_text="Мар 2024 — сейчас · 2 года 6 мес",
                start_date="2024-03-01",
                is_dev_role=False,
                order=3,
                tech_stack="",
                description="<p>Прямые продажи, развитие портфеля клиентов, пресейл, CRM, аналитика.</p>",
            ),
            dict(
                company="Ukaimpex",
                position="Руководитель отдела продаж",
                location="Актау",
                period_text="Ноя 2022 — Фев 2024 · 1 год 4 мес",
                start_date="2022-11-01",
                is_dev_role=False,
                order=4,
                tech_stack="",
                description="<p>Стратегия продаж, подбор и обучение менеджеров, KPI, ключевые клиенты.</p>",
            ),
            dict(
                company="Сбер",
                position="Менеджер по работе с клиентами",
                location="Москва",
                period_text="Фев 2022 — Сен 2022 · 8 мес",
                start_date="2022-02-01",
                is_dev_role=False,
                order=5,
                tech_stack="",
                description="<p>Обработка обращений, продажи, постпродажное сопровождение, CRM.</p>",
            ),
        ]
        for exp in experiences:
            Experience.objects.create(**exp)

        SkillCategory.objects.all().delete()
        categories = {
            "Backend и фреймворки": [
                "Python",
                "Django",
                "Django REST Framework",
                "Flask",
                "FastAPI",
                "Celery",
            ],
            "Данные и хранилища": ["PostgreSQL", "REST API", "JSON API", "Redis"],
            "AI / мультиагентные системы": ["LangGraph", "Scrapy"],
            "Инструменты и практики": [
                "Docker",
                "Docker Compose",
                "CI/CD",
                "Git",
                "GitHub",
                "Pytest",
                "Postman",
                "Agile",
                "Алгоритмы и структуры данных",
                "Оптимизация кода",
            ],
        }
        for i, (cat_title, skills) in enumerate(categories.items()):
            category = SkillCategory.objects.create(title=cat_title, order=i)
            for j, skill_name in enumerate(skills):
                Skill.objects.create(category=category, name=skill_name, order=j)

        EducationItem.objects.all().delete()
        EducationItem.objects.create(
            title="Python-разработчик, backend расширенный курс",
            place="Yandex Practicum",
            date_text="2026",
            order=1,
            description="600+ часов практики, 8 учебных проектов: REST API, Django, FastAPI, PostgreSQL, Docker.",
        )
        EducationItem.objects.create(
            title="Сертификат «Python-разработчик. Расширенный»",
            place="Yandex Practicum",
            date_text="2026",
            order=2,
            description="Сертификат о прохождении программы.",
        )
        EducationItem.objects.create(
            title="Электроника, электротехника, электромеханика",
            place="Académie de Strasbourg, Франция",
            date_text="2009",
            order=3,
            description="Высшее образование.",
        )

        Language.objects.all().delete()
        Language.objects.create(name="Русский", level="Родной", order=1)
        Language.objects.create(
            name="Английский", level="B2 — Средне-продвинутый", order=2
        )
        Language.objects.create(name="Французский", level="C1 — Продвинутый", order=3)

        self.stdout.write(self.style.SUCCESS("Резюме заполнено."))
