from django.utils.text import slugify

# Русская -> латинская транслитерация для слагов (как в URL блога)
_TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def translit_slug(text: str, max_len: int = 50) -> str:
    """Русский текст -> латинский слаг: транслитерация + дефисы.

    Усекается до max_len (максимум SlugField), чтобы длинные заголовки
    не падали с DataError на БД. Пример: «Путь» -> «put», «Код» -> «kod».
    """
    transliterated = ''.join(_TRANSLIT.get(ch, ch) for ch in text.lower())
    slug = slugify(transliterated)
    return slug[:max_len].rstrip('-')
