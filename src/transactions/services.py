from django.db import IntegrityError

from .models import Space


def create_space(user, name):
    """Создать пространство для пользователя. Вернуть (space, error)."""
    name = name.strip()
    if not name:
        return None, 'Введите название пространства.'
    if len(name) > 20:
        return None, 'Название не должно превышать 20 символов.'
    try:
        space = Space.objects.create(user=user, name=name)
        return space, None
    except IntegrityError:
        return None, f'Пространство с именем «{name.lower()}» уже существует.'


def rename_space(space, name):
    """Переименовать пространство. Вернуть (success, error)."""
    name = name.strip()
    if not name:
        return False, 'Введите название пространства.'
    if len(name) > 20:
        return False, 'Название не должно превышать 20 символов.'
    try:
        space.name = name
        space.save()
        return True, None
    except IntegrityError:
        return False, f'Пространство с именем «{name.lower()}» уже существует.'


def delete_space(space, owner):
    """Удалить пространство владельца. Переключить current_space если нужно. Вернуть (success, error)."""
    if Space.objects.filter(user=owner).count() <= 1:
        return False, 'Нельзя удалить единственное пространство.'
    if owner.core_settings.current_space == space:
        other = Space.objects.filter(user=owner).exclude(pk=space.pk).first()
        owner.core_settings.current_space = other
        owner.core_settings.save()
    space.delete()
    return True, None
