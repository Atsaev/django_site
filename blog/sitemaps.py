from django.contrib.sitemaps import Sitemap

from .models import Post


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Post.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        # у поста нет updated_at — последнее изменение публикации
        return obj.published_at
