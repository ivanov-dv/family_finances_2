from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect

from transactions.models import LinkedUserToSpace

SPACE_ROLE_OWNER = 'own_space'
SPACE_ROLE_EDITOR = LinkedUserToSpace.EDITOR
SPACE_ROLE_VIEWER = LinkedUserToSpace.VIEWER

SPACE_EDIT_ROLES = (SPACE_ROLE_OWNER, SPACE_ROLE_EDITOR)


def get_space_role(user, space):
    """Вернуть роль пользователя в пространстве: own_space/edit_space/view_space или None."""
    if not space:
        return None
    if space.user_id == user.id:
        return SPACE_ROLE_OWNER
    link = LinkedUserToSpace.objects.filter(
        space=space, linked_user=user
    ).only('role').first()
    return link.role if link else None


def can_edit_space(role):
    return role in SPACE_EDIT_ROLES


def is_space_owner(role):
    return role == SPACE_ROLE_OWNER


class CurrentSpaceEditMixin(UserPassesTestMixin):
    """Блокирует POST если роль пользователя в current_space не позволяет редактирование."""

    def test_func(self):
        if self.request.method != 'POST':
            return True
        space = self.request.user.core_settings.current_space
        return can_edit_space(get_space_role(self.request.user, space))

    def handle_no_permission(self):
        messages.error(self.request, 'Недостаточно прав для изменения данного пространства.')
        return redirect(self.request.path)
