"""Утилиты подчистки файлов при удалении/замене.

Ничего не импортируют из моделей — принимают модель/поле как параметры.
Каждое приложение (blog/portfolio/resume) подключает их к своим полям в
собственном ready() с partial(..., field_name=\"...\", weak=False).
"""


def cleanup_file_on_delete(sender, instance, field_name, **kwargs):
    """Удаляет привязанный файл с диска при удалении записи."""
    file_field = getattr(instance, field_name, None)
    if file_field:
        file_field.delete(save=False)


def cleanup_file_on_change(sender, instance, field_name, **kwargs):
    """Удаляет старый файл с диска при замене новым."""
    if not instance.pk:
        return  # новая запись — старого файла ещё нет
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    old_file = getattr(old_instance, field_name, None)
    new_file = getattr(instance, field_name, None)
    if old_file and old_file != new_file:
        old_file.delete(save=False)
