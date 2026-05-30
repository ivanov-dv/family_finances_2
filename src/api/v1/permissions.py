from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS, BasePermission

from transactions.permissions import can_edit_space, get_space_role
from users.models import User


def _url_user(view):
    """Пользователь, от имени которого идёт запрос (user_id из URL)."""
    return get_object_or_404(User, pk=view.kwargs['user_id'])


class CanEditCurrentSpace(BasePermission):
    """Небезопасные методы требуют права редактирования текущего пространства."""

    message = 'Недостаточно прав для изменения данного пространства.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = _url_user(view)
        return can_edit_space(
            get_space_role(user, user.core_settings.current_space)
        )


class IsSpaceOwner(BasePermission):
    """Небезопасные методы над Space/участниками — только владелец (user_id из URL)."""

    message = 'Управление пространством доступно только владельцу.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == _url_user(view).id
