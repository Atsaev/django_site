from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from portfolio.models import Project

from .models import Category, Challenge, JobSearchStats, Post


class ChallengeModelTests(TestCase):
    def test_day_number_and_progress(self):
        challenge = Challenge.objects.create(
            name='30 дней',
            start_date=date.today() - timedelta(days=9),
            days_total=30,
        )
        self.assertEqual(challenge.day_number(), 10)
        self.assertEqual(challenge.progress(), 33)

    def test_day_number_capped_at_total(self):
        challenge = Challenge.objects.create(
            name='30 дней',
            start_date=date.today() - timedelta(days=100),
            days_total=30,
        )
        self.assertEqual(challenge.day_number(), 30)
        self.assertEqual(challenge.progress(), 100)


class BlogViewsTests(TestCase):
    def setUp(self):
        # дефолтные рубрики уже создаются миграцией 0003
        self.category, _ = Category.objects.get_or_create(name='Код')  # slug: kod
        self.path_category, _ = Category.objects.get_or_create(name='Путь')  # slug: put
        self.post = Post.objects.create(
            title='Первый пост',
            category=self.category,
            status='published',
            published_at=date(2026, 5, 1),
        )
        self.path_post = Post.objects.create(
            title='День 5: первые отклики',
            category=self.path_category,
            status='published',
            published_at=date(2026, 5, 12),
        )

    def test_post_list_renders(self):
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Первый пост')

    def test_path_timeline_renders_and_sorted_ascending(self):
        response = self.client.get(reverse('path_timeline'))
        self.assertEqual(response.status_code, 200)
        posts = list(response.context['posts'])
        self.assertEqual(posts, sorted(posts, key=lambda p: p.published_at))
        self.assertContains(response, 'День 5: первые отклики')

    def test_post_list_widgets(self):
        Challenge.objects.create(
            name='30 дней', start_date=date.today() - timedelta(days=4), days_total=30,
        )
        JobSearchStats.objects.create(pk=1, applications=5, interviews=2, offers=1)
        response = self.client.get(reverse('post_list'))
        self.assertContains(response, 'День 5 из 30')
        self.assertContains(response, 'Отклики: <strong>5</strong>')
        self.assertContains(response, 'Собеседования: <strong>2</strong>')
        self.assertContains(response, 'Офферы: <strong>1</strong>')

    def test_widgets_hidden_when_empty(self):
        response = self.client.get(reverse('post_list'))
        self.assertNotContains(response, 'из 30')
        self.assertNotContains(response, 'Отклики:')

    def test_post_detail_links_project(self):
        Project.objects.create(
            title='CVE Agent',
            slug='cve-agent',
            short_description='desc',
            tech_stack='Python',
        )
        self.post.project_slug = 'cve-agent'
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#project-cve-agent')
