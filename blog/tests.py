from datetime import date, timedelta
from io import BytesIO
from tempfile import mkdtemp
from types import SimpleNamespace

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from config.storage import MediaFileSystemStorage
from portfolio.models import Project

from .admin import PostAdmin, PostAdminForm
from .models import REACTIONS, Category, Challenge, JobSearchStats, Post, PostReaction, Tag, inflate_reactions
from .translit import translit_slug


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
