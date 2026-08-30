from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from portfolio.models import Project

from .models import Category, Challenge, JobSearchStats, Post


class ChallengeModelTests(TestCase):
    def test_current_day_and_progress(self):
        challenge = Challenge.objects.create(
            title='30 дней после курса',
            start_date=date.today() - timedelta(days=9),
            total_days=30,
        )
        self.assertEqual(challenge.current_day, 10)
        self.assertEqual(challenge.progress_percent, 33)

    def test_current_day_capped_and_slug_auto(self):
        challenge = Challenge.objects.create(
            title='30 дней после курса',
            start_date=date.today() - timedelta(days=100),
            total_days=30,
        )
        self.assertEqual(challenge.current_day, 30)
        self.assertEqual(challenge.progress_percent, 100)
        self.assertEqual(challenge.slug, '30-dney-posle-kursa')

    def test_days_left(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=9), total_days=30,
        )
        self.assertEqual(challenge.days_left(), 20)

    def test_creating_active_deactivates_others(self):
        first = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=5),
        )
        second = Challenge.objects.create(
            title='100 дней кода', start_date=date.today() - timedelta(days=2),
        )
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(Challenge.objects.filter(is_active=True).count(), 1)

    def test_reactivating_switches_active(self):
        first = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=5),
        )
        second = Challenge.objects.create(
            title='100 дней кода', start_date=date.today() - timedelta(days=2),
        )
        first.is_active = True
        first.save()
        second.refresh_from_db()
        self.assertTrue(first.is_active)
        self.assertFalse(second.is_active)

    def test_resaving_active_keeps_self_active(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=5),
        )
        challenge.save()  # повторное сохранение не должно деактивировать сам себя
        challenge.refresh_from_db()
        self.assertTrue(challenge.is_active)
        self.assertEqual(Challenge.objects.filter(is_active=True).count(), 1)


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

    def test_timeline_for_any_category(self):
        response = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Первый пост')
        posts = list(response.context['posts'])
        self.assertEqual(posts, sorted(posts, key=lambda p: p.published_at))

    def test_timeline_shows_category_description(self):
        self.category.description = 'Разбор FastAPI от установки до деплоя'
        self.category.save()
        response = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        self.assertContains(response, 'Разбор FastAPI от установки до деплоя')

    def test_timeline_orders_by_published_not_created(self):
        # создан раньше, но опубликован позже — в истории встанет позже
        early_created = Post.objects.create(
            title='Написан раньше, опубликован позже', category=self.category,
            status='published', published_at=date(2026, 5, 9),
        )
        late_created = Post.objects.create(
            title='Написан позже, опубликован раньше', category=self.category,
            status='published', published_at=date(2026, 5, 1),
        )
        response = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        pks = [p.pk for p in response.context['posts']]
        # порядок ведёт дата публикации, а не дата создания
        self.assertLess(pks.index(late_created.pk), pks.index(early_created.pk))

    def test_timeline_fallback_text(self):
        response = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        self.assertContains(response, 'Хронологический вид рубрики')

    def test_timeline_toggle_on_category_page(self):
        Post.objects.create(
            title='Второй пост', category=self.category,
            status='published', published_at=date(2026, 5, 2),
        )
        response = self.client.get(reverse('post_list_category', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'таймлайн')

    def test_timeline_toggle_hidden_for_single_post(self):
        response = self.client.get(reverse('post_list_category', args=[self.category.slug]))
        self.assertNotContains(response, 'timeline-toggle')

    def test_post_list_widgets(self):
        Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=4), total_days=30,
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

    def test_day_number_auto_assigned(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=1),
        )
        p1 = Post.objects.create(
            title='Пост 1', challenge=challenge, status='published',
            published_at=date(2026, 5, 1),
        )
        p2 = Post.objects.create(
            title='Пост 2', challenge=challenge, status='published',
            published_at=date(2026, 5, 2),
        )
        self.assertEqual(p1.day_number, 1)
        self.assertEqual(p2.day_number, 2)

    def test_challenge_detail_page_orders_by_day(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        Post.objects.create(
            title='День второй', challenge=challenge, day_number=2,
            status='published', published_at=date(2026, 5, 2),
        )
        Post.objects.create(
            title='День первый', challenge=challenge, day_number=1,
            status='published', published_at=date(2026, 5, 1),
        )
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'День 3 из 30')
        posts = list(response.context['posts'])
        self.assertEqual([p.day_number for p in posts], [1, 2])

    def test_challenge_timeline_orders_by_day_not_date(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        Post.objects.create(
            title='День 6 (опубликован раньше)', challenge=challenge, day_number=6,
            status='published', published_at=date(2026, 5, 1),
        )
        Post.objects.create(
            title='День 5 (опубликован позже)', challenge=challenge, day_number=5,
            status='published', published_at=date(2026, 5, 9),
        )
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        posts = list(response.context['posts'])
        # даты публикации противоречат номерам — порядок всё равно строго по дням
        self.assertEqual([p.day_number for p in posts], [5, 6])

    def test_challenge_timeline_stable_for_equal_days(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        a = Post.objects.create(
            title='День 5 (первый)', challenge=challenge, day_number=5,
            status='published', published_at=date(2026, 5, 1),
        )
        b = Post.objects.create(
            title='День 5 (второй)', challenge=challenge, day_number=5,
            status='published', published_at=date(2026, 5, 1),
        )
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        posts = list(response.context['posts'])
        # равные day_number — порядок детерминирован по created_at
        self.assertEqual([p.pk for p in posts], [a.pk, b.pk])

    def test_post_detail_shows_challenge_progress(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=4), total_days=30,
        )
        self.post.challenge = challenge
        self.post.save()  # day_number проставится автоматически
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'challenge-progress')
        self.assertContains(response, 'День 1 из 30')
        self.assertContains(response, challenge.slug)

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

    def test_home_shows_challenge_strip(self):
        Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=4), total_days=30,
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'challenge-strip')
        self.assertContains(response, 'День 5 из 30')
