from datetime import date, datetime, timedelta
from io import BytesIO
from tempfile import mkdtemp
from types import SimpleNamespace

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from config.storage import MediaFileSystemStorage
from portfolio.models import Project
from resume.models import Profile

from .admin import PostAdmin, PostAdminForm
from .models import (
    REACTIONS,
    Category,
    Challenge,
    Post,
    PostReaction,
    Tag,
    inflate_reactions,
)
from .translit import translit_slug


def _aware(d: date) -> datetime:
    """DateTimeField хранит aware datetime в UTC — из даты делаем aware по TIME_ZONE."""
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new('RGB', (1200, 630), 'red').save(buf, 'PNG')
    return buf.getvalue()


class ChallengeModelTests(TestCase):
    def test_current_day_and_progress(self):
        challenge = Challenge.objects.create(
            title='30 дней после курса',
            start_date=date.today() - timedelta(days=9),
            total_days=30,
        )
        self.assertEqual(challenge.current_day, 10)
        # постов нет — прогресс 0 даже несмотря на прошедшие календарные дни
        self.assertEqual(challenge.progress_percent, 0)
        self.assertEqual(challenge.done_count, 0)

    def test_current_day_capped_and_slug_auto(self):
        challenge = Challenge.objects.create(
            title='30 дней после курса',
            start_date=date.today() - timedelta(days=100),
            total_days=30,
        )
        # период закончился давно, но прогресс опирается на факт постов
        self.assertEqual(challenge.current_day, 101)
        self.assertTrue(challenge.finished())
        self.assertEqual(challenge.progress_percent, 0)
        self.assertEqual(challenge.status(), 'missed')
        self.assertEqual(challenge.slug, '30-dney-posle-kursa')

    def test_days_left(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=9), total_days=30,
        )
        self.assertEqual(challenge.days_left(), 20)

    def test_days_grid_states(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2), total_days=5,
        )
        p = Post.objects.create(
            title='День 2', challenge=challenge, status='published',
        )
        # в обход save: день 2 закрыт постом (save посчитал бы текущий день)
        Post.objects.filter(pk=p.pk).update(day_number=2)
        grid = {d['n']: d['state'] for d in challenge.days_grid()}
        # сегодня — день 3; день 2 закрыт; день 1 пропущен (миновал без поста); 4 и 5 впереди
        self.assertEqual(grid[1], 'missed')
        self.assertEqual(grid[2], 'done')
        self.assertEqual(grid[3], 'today')
        self.assertEqual(grid[4], 'future')
        self.assertEqual(grid[5], 'future')
        self.assertEqual(len(grid), 5)

    def test_status_active_then_done(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=1), total_days=2,
        )
        self.assertEqual(challenge.status(), 'active')
        a = Post.objects.create(title='1', challenge=challenge, status='published')
        b = Post.objects.create(title='2', challenge=challenge, status='published')
        # в обход save: посты закрывают дни 1 и 2
        Post.objects.filter(pk=a.pk).update(day_number=1)
        Post.objects.filter(pk=b.pk).update(day_number=2)
        # уже наступил день 3 (период из 2 дней закончился) и оба закрыты
        self.assertEqual(challenge.status(), 'done')

    def test_status_missed_when_not_all_days_written(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=3), total_days=2,
        )
        # день 1 пропущен, день 2 закрыт — итог провален
        Post.objects.create(title='2', challenge=challenge, day_number=2, status='published')
        self.assertEqual(challenge.status(), 'missed')

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

    def test_cannot_shrink_total_days_below_written_posts(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2), total_days=30,
        )
        p = Post.objects.create(
            title='День 30', challenge=challenge, status='published',
        )
        # в обход save: пост закрывает день 30
        Post.objects.filter(pk=p.pk).update(day_number=30)
        # уменьшить до 20 нельзя — есть пост с днём 30
        challenge.total_days = 20
        with self.assertRaises(ValidationError):
            challenge.clean()
        # увеличить до 40 — допустимо
        challenge.total_days = 40
        challenge.clean()  # не должно бросить

    def test_manual_day_number_ignored_on_save(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2), total_days=30,
        )
        # «День 32» игнорируется: save() пересчитает день от created_at
        # (первый день челленджа — вчера, значит пост сегодня получит день 3)
        post = Post.objects.create(
            title='Вне срока', challenge=challenge, day_number=32, status='published',
        )
        self.assertEqual(post.day_number, 3)
        # ручной ввод больше не может создать день, выходящий за сроки челленджа
        challenge.total_days = 30
        challenge.clean()  # не должно бросить

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
        # дефолтные рубрики уже создаются миграцией 0003; bf-0017 ставит Путь is_timeline
        self.category, _ = Category.objects.get_or_create(name='Код')  # slug: kod
        self.path_category, _ = Category.objects.get_or_create(name='Путь')  # slug: put (is_timeline=True из миграции)
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

    def test_search_by_title(self):
        response = self.client.get(reverse('post_list'), {'q': 'Первый'})
        self.assertContains(response, 'Первый пост')
        self.assertNotContains(response, 'День 5: первые отклики')

    def test_search_by_tag(self):
        tag, _ = Tag.objects.get_or_create(name='FastAPI')
        self.post.tags.add(tag)
        response = self.client.get(reverse('post_list'), {'q': 'fastapi'})
        self.assertContains(response, 'Первый пост')

    def test_search_by_content(self):
        self.post.content = '<p>секретное слово из текста</p>'
        self.post.save()
        response = self.client.get(reverse('post_list'), {'q': 'секретное'})
        self.assertContains(response, 'Первый пост')

    def test_search_empty_query_returns_all(self):
        response = self.client.get(reverse('post_list'), {'q': '   '})
        self.assertContains(response, 'Первый пост')
        self.assertContains(response, 'День 5: первые отклики')

    def test_search_no_results(self):
        response = self.client.get(reverse('post_list'), {'q': 'несуществующееслово'})
        self.assertContains(response, 'ничего не найдено')

    def test_search_shows_count(self):
        response = self.client.get(reverse('post_list'), {'q': 'Первый'})
        self.assertContains(response, 'найдено:')

    def test_search_htmx_returns_partial(self):
        response = self.client.get(
            reverse('post_list'), {'q': 'Первый'}, HTTP_HX_REQUEST='true',
        )
        self.assertContains(response, 'cat-chips')
        self.assertNotContains(response, 'search-box')

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
        self.path_post.applications_count = 5
        self.path_post.save()
        response = self.client.get(reverse('post_list'))
        self.assertContains(response, 'День 5 из 30')
        # статистика поиска работы НЕ на общей ленте — она переехала на таймлайн «Пути»
        self.assertNotContains(response, 'Отклики: <strong>5</strong>')

    def test_job_stats_on_path_timeline_only(self):
        self.path_post.applications_count = 12
        self.path_post.interviews_count = 3
        self.path_post.offers_count = 1
        self.path_post.save()
        # пост другой категории тоже вносит вклад в общую сумму
        self.post.applications_count = 1
        self.post.save()
        path = self.client.get(reverse('path_timeline'))
        self.assertContains(path, 'Отклики: <strong>13</strong>')
        self.assertContains(path, 'Собеседования: <strong>3</strong>')
        self.assertContains(path, 'Офферы: <strong>1</strong>')
        # на другом таймлайне (рубрика «Код») статистики нет
        other = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        self.assertNotContains(other, 'Отклики:')

    def test_employment_status_on_path_timeline(self):
        Profile.objects.get_or_create(
            pk=1,
            defaults={
                'name': 'Тест', 'role': 'Backend', 'location': 'Москва',
                'about': '<p>x</p>', 'email': 't@t.ru', 'employment_status': 'actively_looking',
            },
        )
        path = self.client.get(reverse('path_timeline'))
        self.assertContains(path, 'В активном поиске')
        other = self.client.get(reverse('category_timeline', args=[self.category.slug]))
        self.assertNotContains(other, 'path-status')

    def test_job_badges_on_path_timeline(self):
        self.path_post.applications_count = 2
        self.path_post.interviews_count = 1
        self.path_post.save()
        path = self.client.get(reverse('path_timeline'))
        self.assertContains(path, 'откликов: 2')
        self.assertContains(path, 'собесов: 1')
        self.assertNotContains(path, 'офферов:')  # счётчик офферов 0 — бейджа нет

    def test_job_event_day_block_on_post_detail(self):
        self.path_post.applications_count = 3
        self.path_post.offers_count = 1
        self.path_post.save()
        r = self.client.get(reverse('post_detail', args=[self.path_post.slug]))
        self.assertContains(r, 'job-event-day')
        self.assertContains(r, 'отправлено откликов: 3')
        self.assertContains(r, 'оффер: 1')

    def test_no_job_event_block_when_zero(self):
        r = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertNotContains(r, 'job-event-day')

    def test_widgets_hidden_when_empty(self):
        response = self.client.get(reverse('post_list'))
        self.assertNotContains(response, 'из 30')
        self.assertNotContains(response, 'Отклики:')

    def test_day_number_auto_assigned(self):
        start = date.today() - timedelta(days=1)
        challenge = Challenge.objects.create(
            title='30 дней', start_date=start,
        )
        # оба поста созданы в один и тот же календарный день — им ставится
        # один и тот же day_number (= 2), посчитанный от created_at по дате старта.
        p1 = Post.objects.create(
            title='Пост 1', challenge=challenge, status='published',
        )
        p2 = Post.objects.create(
            title='Пост 2', challenge=challenge, status='published',
        )
        self.assertEqual(p1.day_number, 2)
        self.assertEqual(p2.day_number, 2)

    def test_day_number_clamped_to_total_days_on_create(self):
        start = date.today() - timedelta(days=100)
        challenge = Challenge.objects.create(
            title='100 дней', start_date=start, total_days=30,
        )
        # постов с day_number 101 нет — день не должен выйти за рамки челленджа
        p = Post.objects.create(title='Пост', challenge=challenge, status='published')
        self.assertEqual(p.day_number, 30)

    def test_challenge_detail_page_orders_by_day(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        first = Post.objects.create(
            title='День первый', challenge=challenge, status='published',
            published_at=date(2026, 5, 1),
        )
        second = Post.objects.create(
            title='День второй', challenge=challenge, status='published',
            published_at=date(2026, 5, 2),
        )
        # в обход save: задаём дни 1 и 2 явно (save пересчитал бы по created_at)
        Post.objects.filter(pk=first.pk).update(
            created_at=_aware(challenge.start_date - timedelta(days=1)), day_number=1)
        Post.objects.filter(pk=second.pk).update(
            created_at=_aware(challenge.start_date), day_number=2)
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'День 3 из 30')
        posts = list(response.context['posts'])
        self.assertEqual([p.day_number for p in posts], [1, 2])

    def test_challenge_timeline_orders_by_day_not_date(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        # создаём посты так, чтобы created_at попал в дни 5 и 6 челленджа
        day6 = Post.objects.create(
            title='День 6 (опубликован раньше)', challenge=challenge, status='published',
            published_at=date(2026, 5, 1),
        )
        day5 = Post.objects.create(
            title='День 5 (опубликован позже)', challenge=challenge, status='published',
            published_at=date(2026, 5, 9),
        )
        Post.objects.filter(pk=day6.pk).update(
            created_at=_aware(challenge.start_date + timedelta(days=5)), day_number=6)
        Post.objects.filter(pk=day5.pk).update(
            created_at=_aware(challenge.start_date + timedelta(days=4)), day_number=5)
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        posts = list(response.context['posts'])
        # даты публикации противоречат номерам — порядок всё равно строго по дням
        self.assertEqual([p.day_number for p in posts], [5, 6])

    def test_challenge_timeline_stable_for_equal_days(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=2),
        )
        a = Post.objects.create(
            title='День 5 (первый)', challenge=challenge, status='published',
            published_at=date(2026, 5, 1),
        )
        b = Post.objects.create(
            title='День 5 (второй)', challenge=challenge, status='published',
            published_at=date(2026, 5, 1),
        )
        response = self.client.get(reverse('challenge_detail', args=[challenge.slug]))
        posts = list(response.context['posts'])
        # посты созданы в один день (равные day_number) — порядок по created_at
        self.assertEqual([p.pk for p in posts], [a.pk, b.pk])

    def test_post_detail_shows_challenge_progress(self):
        challenge = Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=4), total_days=30,
        )
        self.post.challenge = challenge
        self.post.save()  # day_number проставится автоматически от created_at
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'challenge-progress')
        self.assertContains(response, 'День 5 из 30')
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

    def test_syntax_highlighting_loaded(self):
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'highlight.min.js')
        self.assertContains(response, 'atom-one-dark')

    def test_code_block_language_class_preserved(self):
        self.post.content = (
            '<h2>Пример</h2>'
            '<pre><code class="language-python">def f():\n    return 1</code></pre>'
        )
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'language-python')

    def test_post_detail_shows_reactions(self):
        PostReaction.objects.create(post=self.post, reaction='like')
        PostReaction.objects.create(post=self.post, reaction='dislike')
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'reactions')
        self.assertContains(response, '👍')
        self.assertContains(response, '👎')

    def test_react_add(self):
        response = self.client.post(
            reverse('post_react', args=[self.post.slug]),
            {'reaction': 'like', 'action': 'add'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostReaction.objects.filter(post=self.post, reaction='like').count(), 1)

    def test_react_remove_decrements(self):
        PostReaction.objects.create(post=self.post, reaction='like')
        PostReaction.objects.create(post=self.post, reaction='like')
        response = self.client.post(
            reverse('post_react', args=[self.post.slug]),
            {'reaction': 'like', 'action': 'remove'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostReaction.objects.filter(post=self.post, reaction='like').count(), 1)

    def test_react_remove_at_zero_keeps_zero(self):
        response = self.client.post(
            reverse('post_react', args=[self.post.slug]),
            {'reaction': 'dislike', 'action': 'remove'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostReaction.objects.filter(post=self.post, reaction='dislike').count(), 0)

    def test_react_unknown_reaction_400(self):
        response = self.client.post(
            reverse('post_react', args=[self.post.slug]),
            {'reaction': 'nope', 'action': 'add'},
        )
        self.assertEqual(response.status_code, 400)

    def test_react_unknown_action_400(self):
        response = self.client.post(
            reverse('post_react', args=[self.post.slug]),
            {'reaction': 'like', 'action': 'nope'},
        )
        self.assertEqual(response.status_code, 400)

    def test_react_get_405(self):
        response = self.client.get(reverse('post_react', args=[self.post.slug]))
        self.assertEqual(response.status_code, 405)

    def test_react_unpublished_404(self):
        draft = Post.objects.create(
            title='Черновик', category=self.category, status='draft',
        )
        response = self.client.post(
            reverse('post_react', args=[draft.slug]),
            {'reaction': 'like', 'action': 'add'},
        )
        self.assertEqual(response.status_code, 404)

    def test_inflate_reactions_random(self):
        inflate_reactions(self.post, 10)
        rows = PostReaction.objects.filter(post=self.post)
        self.assertEqual(rows.count(), 10)
        self.assertTrue(all(r.reaction in REACTIONS for r in rows))

    def test_admin_inflate_on_save(self):
        form = SimpleNamespace(cleaned_data={'inflate_reactions': True, 'inflate_count': 7})
        PostAdmin(Post, admin.site).save_model(None, self.post, form, False)
        self.assertEqual(PostReaction.objects.filter(post=self.post).count(), 7)

    def test_admin_no_inflate_when_unchecked(self):
        form = SimpleNamespace(cleaned_data={'inflate_reactions': False, 'inflate_count': 7})
        PostAdmin(Post, admin.site).save_model(None, self.post, form, False)
        self.assertEqual(PostReaction.objects.filter(post=self.post).count(), 0)

    def test_admin_form_shows_current_counts(self):
        PostReaction.objects.create(post=self.post, reaction='like')
        PostReaction.objects.create(post=self.post, reaction='like')
        PostReaction.objects.create(post=self.post, reaction='dislike')
        form = PostAdminForm(instance=self.post)
        help_text = form.fields['inflate_reactions'].help_text
        self.assertIn('Сейчас:', help_text)
        self.assertIn('👍 2', help_text)
        self.assertIn('👎 1', help_text)

    def test_og_tags_on_post(self):
        self.post.excerpt = 'Краткое описание'
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'og:type" content="article"')
        self.assertContains(response, 'og:title" content="Первый пост"')
        self.assertContains(response, 'og:description" content="Краткое описание"')
        self.assertContains(response, 'twitter:card" content="summary"')

    def test_og_description_falls_back_to_title(self):
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'og:description" content="Первый пост"')

    def test_og_image_when_post_has_image(self):
        self.post.content = '<p>текст</p><figure><img src="/media/test.png" alt="x"></figure>'
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'og:image" content="http://testserver/media/test.png"')

    def test_og_image_absent_without_image(self):
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertNotContains(response, 'og:image')

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_og_image_cover_priority(self):
        self.post.cover_image = SimpleUploadedFile(
            'cover.png', _png_bytes(), content_type='image/png',
        )
        self.post.content = '<img src="/media/in-content.png" alt="x">'
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'http://testserver' + self.post.cover_image.url)
        self.assertNotContains(response, 'og:image" content="http://testserver/media/in-content.png"')

    def test_og_website_on_home(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'og:type" content="website"')
        self.assertContains(response, 'og:site_name" content="atsaev-dev.ru"')

    def test_meta_description_on_post(self):
        self.post.excerpt = 'Описание для меты'
        self.post.save()
        response = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertContains(response, 'name="description" content="Описание для меты"')

    def test_meta_description_on_home(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'name="description"')

    def test_sitemap_contains_posts(self):
        response = self.client.get(reverse('sitemap'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.post.slug)

    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User-agent: *')
        self.assertContains(response, 'sitemap.xml')

    def test_admin_reset_reactions_action(self):
        PostReaction.objects.create(post=self.post, reaction='like')
        PostReaction.objects.create(post=self.post, reaction='dislike')
        admin_obj = PostAdmin(Post, admin.site)
        admin_obj.message_user = lambda request, message: None
        qs = Post.objects.filter(pk=self.post.pk)
        admin_obj.reset_reactions(None, qs)
        self.assertEqual(PostReaction.objects.filter(post=self.post).count(), 0)

    def test_reset_reactions_action_registered(self):
        user = User.objects.create_superuser('admin', 'a@a.ru', 'x')
        req = RequestFactory().get('/admin/blog/post/')
        req.user = user
        admin_obj = PostAdmin(Post, admin.site)
        self.assertIn('reset_reactions', admin_obj.get_actions(req))

    def test_translit_slug_truncated_to_max_len(self):
        long_title = 'Почему PostgreSQL — это не так страшно, как кажется новичку после курса'
        slug = translit_slug(long_title)
        self.assertLessEqual(len(slug), 50)
        self.assertFalse(slug.endswith('-'))

    def test_seed_command_creates_posts(self):
        before = Post.objects.filter(status='published').count()
        call_command('seed_demo_posts', count=3)
        self.assertEqual(Post.objects.filter(status='published').count(), before + 3)

    def _query_count(self, url):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx.captured_queries)

    def test_post_list_queries_constant_with_scale(self):
        base = self._query_count(reverse('post_list'))
        for i in range(20):
            Post.objects.create(
                title=f'Масштаб {i}', category=self.category,
                status='published', published_at=date(2026, 5, i + 1),
            )
        # N+1 проявился бы ростом запросов — а их количество не меняется
        self.assertEqual(self._query_count(reverse('post_list')), base)

    def test_post_detail_queries_constant_with_scale(self):
        base = self._query_count(reverse('post_detail', args=[self.post.slug]))
        for i in range(20):
            Post.objects.create(
                title=f'Масштаб {i}', category=self.category,
                status='published', published_at=date(2026, 5, i + 1),
            )
        # related_posts ограничены и остаются константными запросами
        self.assertEqual(self._query_count(reverse('post_detail', args=[self.post.slug])), base)

    def test_home_shows_challenge_strip(self):
        Challenge.objects.create(
            title='30 дней', start_date=date.today() - timedelta(days=4), total_days=30,
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'challenge-strip')
        self.assertContains(response, 'День 5 из 30')

    def test_media_storage_transliterates_cyrillic_filenames(self):
        storage = MediaFileSystemStorage()
        self.assertEqual(
            storage.get_available_name('Снимок экрана 2024.png'),
            'snimok-ekrana-2024.png',
        )
        # латинские имена почти не меняются
        self.assertEqual(storage.get_available_name('hello world.jpg'), 'hello-world.jpg')
        # дубли получают суффикс, а не склеиваются
        self.assertTrue(storage.get_available_name('hello-world.jpg').startswith('hello-world'))
        # расширение сохраняется, транслит не трогает его
        self.assertTrue(storage.get_available_name('Отчет.pdf').endswith('.pdf'))
        # upload_to-префикс (каталог) сохраняется, транслит только имени
        self.assertEqual(
            storage.get_available_name('resume/Снимок экрана.png'),
            'resume/snimok-ekrana.png',
        )
        self.assertEqual(
            storage.get_available_name('posts/Отчет.pdf'),
            'posts/otchet.pdf',
        )
        # вложенные каталоги тоже
        self.assertEqual(storage.get_available_name('a/b/Привет.png'), 'a/b/privet.png')


class FileCleanupTests(TestCase):
    """Подчистка файлов: при замене — старый с диска, при удалении записи — её файл."""

    def _make_cover(self, name='cover.png'):
        return SimpleUploadedFile(name, _png_bytes(), content_type='image/png')

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_new_post_creation_does_not_trigger_old_file_cleanup(self):
        # создание с нуля не должно падать на Post.objects.get(pk=None)
        post = Post.objects.create(
            title='Новый', category=self._cat(), cover_image=self._make_cover(),
            status='published', published_at=date(2026, 6, 1),
        )
        self.assertIsNotNone(post.pk)
        self.assertTrue(post.cover_image)

    def _cat(self):
        from .models import Category
        return Category.objects.get_or_create(name='Код')[0]

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_replacing_photo_cleans_old_file(self):
        post = Post.objects.create(
            title='Тест замены', category=self._cat(), cover_image=self._make_cover('old1.png'),
            status='published', published_at=date(2026, 6, 2),
        )
        old_name = post.cover_image.name
        self.assertTrue(post.cover_image.storage.exists(old_name))

        # заменяем файл
        post.cover_image = self._make_cover('new1.png')
        post.save()

        self.assertFalse(post.cover_image.storage.exists(old_name))  # старый удалён
        self.assertTrue(post.cover_image.storage.exists(post.cover_image.name))

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_deleting_post_cleans_cover(self):
        post = Post.objects.create(
            title='Тест удаления', category=self._cat(), cover_image=self._make_cover('del1.png'),
            status='published', published_at=date(2026, 6, 3),
        )
        name = post.cover_image.name
        self.assertTrue(post.cover_image.storage.exists(name))
        post.delete()
        self.assertFalse(post.cover_image.storage.exists(name))  # файл удалён с диска

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_delete_without_cover_does_not_crash(self):
        post = Post.objects.create(
            title='Без обложки', category=self._cat(),
            status='published', published_at=date(2026, 6, 4),
        )
        self.assertIsNone(post.cover_image.name)  # у ProcessedImageField нет файла -> name пустой
        post.delete()  # не должно падать на пустом cover_image
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_signal_connected_exactly_once(self):
        # dispatch_uid гарантирует: даже при повторных ready() cleanup-ресивер один
        from django.db.models.signals import post_delete
        receivers = post_delete._live_receivers(Post)
        cleanup = [r for r in receivers if 'cleanup_file_on_delete' in str(r)]
        self.assertEqual(len(cleanup), 1)
