from django.contrib import messages
from django.shortcuts import redirect

from transactions.models import LinkedUserToSpace

SPACE_ROLE_OWNER = 'own_space'
SPACE_ROLE_EDITOR = LinkedUserToSpace.EDITOR
SPACE_ROLE_VIEWER = LinkedUserToSpace.VIEWER

SPACE_EDIT_ROLES = (SPACE_ROLE_OWNER, SPACE_ROLE_EDITOR)


def get_space_role(user, space):
    """Return owner/editor/viewer role or None for user in space."""
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


class CurrentSpaceEditMixin:
    """Блокирует POST если роль пользователя в current_space не позволяет редактирование."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            space = request.user.core_settings.current_space
            role = get_space_role(request.user, space)
            if not can_edit_space(role):
                messages.error(request, 'Недостаточно прав для изменения данного пространства.')
                return redirect(request.path)
        return super().dispatch(request, *args, **kwargs)
