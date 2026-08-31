from django.core.management.base import BaseCommand

from portfolio.models import Project


class Command(BaseCommand):
    help = "Заполняет портфолио реальными проектами"

    def handle(self, *args, **options):
        Project.objects.all().delete()

        projects = [
            dict(
                title="CVE Agent",
                slug="cve-agent",
                short_description="Мультиагентная система анализа уязвимостей на LangGraph — 4 агента (Analyst → Risk → Mitigation → Reporter). Сокращает разбор CVE с ~30 минут до 2–3.",
                tech_stack="LangGraph, DeepSeek, FastAPI, Docker",
                github_url="https://github.com/Atsaev/cve-agent",
                demo_url="https://atsaev-dev.ru/cve/docs",
                status="live",
                order=1,
            ),
            dict(
                title="Smart Fuzzer",
                slug="smart-fuzzer",
                short_description="LLM-инструмент для автоматической генерации тест-кейсов и поиска уязвимостей в Python-коде без участия человека.",
                tech_stack="DeepSeek, FastAPI, Pydantic, Docker",
                github_url="https://github.com/Atsaev/smart-fuzzer",
                demo_url="https://atsaev-dev.ru/fuzzer/docs",
                status="live",
                order=2,
            ),
            dict(
                title="Security Pipeline",
                slug="security-pipeline",
                short_description="Автоматический пайплайн сбора данных об уязвимостях из NVD API с фильтрацией по критичности и сохранением в БД.",
                tech_stack="Python, SQLAlchemy, Pydantic, Docker",
                github_url="https://github.com/Atsaev/security-pipeline",
                demo_url="",
                status="live",
                order=3,
            ),
            dict(
                title="Foodgram",
                slug="foodgram",
                short_description="Продакшн-сервис публикации рецептов с полным CI/CD-пайплайном через GitHub Actions. Деплой одной командой, время выката — 2 минуты.",
                tech_stack="Django, PostgreSQL, Docker, GitHub Actions",
                github_url="https://github.com/Atsaev/foodgram",
                demo_url="",
                status="live",
                order=4,
            ),
            dict(
                title="Sales Assistant",
                slug="sales-assistant",
                short_description="Десктопное приложение для анализа звонков: real-time транскрипция (Whisper) + анализ диалога локальной LLM (Ollama), без отправки данных наружу.",
                tech_stack="Whisper, Ollama, Python",
                github_url="https://github.com/Atsaev/sales_assistant",
                demo_url="",
                status="wip",
                order=5,
            ),
        ]

        for p in projects:
            Project.objects.create(**p)

        self.stdout.write(self.style.SUCCESS(f"Добавлено проектов: {len(projects)}"))
