from django.db import IntegrityError

from users.models import User

from .exceptions import SpaceError
from .models import LinkedUserToSpace, Space
from .permissions import get_space_role


class SpaceService:
    """Бизнес-логика операций со Space/LinkedUserToSpace."""

    @staticmethod
    def create_space(user: User, name: str) -> Space:
        """Создать пространство для пользователя."""
        name = name.strip()
        if not name:
            raise SpaceError('Введите название пространства.')
        if len(name) > 20:
            raise SpaceError('Название не должно превышать 20 символов.')
        try:
            return Space.objects.create(user=user, name=name)
        except IntegrityError:
            raise SpaceError(f'Пространство с именем «{name.lower()}» уже существует.')

    @staticmethod
    def rename_space(space: Space, name: str) -> None:
        """Переименовать пространство."""
        name = name.strip()
        if not name:
            raise SpaceError('Введите название пространства.')
        if len(name) > 20:
            raise SpaceError('Название не должно превышать 20 символов.')
        try:
            space.name = name
            space.save()
        except IntegrityError:
            raise SpaceError(f'Пространство с именем «{name.lower()}» уже существует.')

    @staticmethod
    def apply_space(user: User, space: Space) -> None:
        """Переключить current_space пользователя."""
        if get_space_role(user, space) is None:
            raise SpaceError('Нет доступа к данному пространству.')
        user.core_settings.current_space = space
        user.core_settings.save()

    @staticmethod
    def leave_space(user: User, space: Space) -> None:
        """Участник покидает пространство."""
        if space.user_id == user.id:
            raise SpaceError('Нельзя покинуть собственное пространство.')
        link = LinkedUserToSpace.objects.filter(space=space, linked_user=user).first()
        if not link:
            raise SpaceError('Вы не являетесь участником данного пространства.')
        if user.core_settings.current_space == space:
            user.core_settings.current_space = None
            user.core_settings.save()
        link.delete()

    @staticmethod
    def delete_space(space: Space, owner: User) -> None:
        """Удалить пространство владельца. Переключить current_space если нужно."""
        if Space.objects.filter(user=owner).count() <= 1:
            raise SpaceError('Нельзя удалить единственное пространство.')
        if owner.core_settings.current_space == space:
            other = Space.objects.filter(user=owner).exclude(pk=space.pk).first()
            owner.core_settings.current_space = other
            owner.core_settings.save()
        space.delete()
