"""Хранилище медиа с транслитерацией имён файлов при загрузке.

Заменяет кириллические имена («Снимок экрана.png») на латиницу
(«snimok-ekrana.png»), чтобы URL был человекочитаемым и без
процентного кодирования (%D0%A1%D0%BD%D0%B8%D0%BC%D0%BE%D0%BA...).
"""
import os

from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename, slugify

# Русская -> латинская транслитерация (общая для слагов и имён файлов)
_TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _translit_text(text: str) -> str:
    """Транслитерация кириллицы -> латиница (остальные символы без изменений)."""
    return ''.join(_TRANSLIT.get(ch, ch) for ch in text.lower())


class MediaFileSystemStorage(FileSystemStorage):
    """FileSystemStorage с транслитерацией имени файла при сохранении."""

    def get_valid_name(self, name: str) -> str:
        # разбиваем на базовое имя и расширение, транслит применяем только к базовому
        base = name
        ext = ''
        if '.' in name:
            base, ext = os.path.splitext(name)

        transliterated = _translit_text(base)
        slug = slugify(transliterated) or 'file'
        # get_valid_filename уже убирает небезопасные символы и пустые имена
        valid = get_valid_filename(f'{slug}{ext}')
        return super().get_valid_name(valid)

    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        # get_valid_name вызывается не всегда (например, через get_available_name),
        # поэтому транслит применяем именно здесь — перед проверкой уникальности
        return super().get_available_name(self.get_valid_name(name), max_length=max_length)

    def _save(self, name: str, content) -> str:
        # страхуемся и на уровне фактической записи (validate/пути во вложенных папках)
        return super()._save(self.get_valid_name(name), content)
