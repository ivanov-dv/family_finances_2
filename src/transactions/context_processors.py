from django.db.models import Q

from .models import Space, Summary
from .permissions import can_edit_space, get_space_role, is_space_owner


def spaces_and_role(request):
    """Список доступных пространств и роль в текущем space (глобально).

    available_spaces — свои + чужие (через LinkedUserToSpace), с атрибутом
    display_name: своё → имя; чужое → «имя · от <owner>».
    current_space_role/can_edit/is_owner — права в активном пространстве.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    core = getattr(user, 'core_settings', None)
    current_space = core.current_space if core else None
    role = get_space_role(user, current_space)

    spaces = (
        Space.objects
        .filter(Q(user=user) | Q(available_linked_users=user))
        .select_related('user')
        .distinct()
        .order_by('name')
    )
    for space in spaces:
        if space.user_id == user.id:
            space.display_name = space.name
        else:
            owner = space.user.first_name or space.user.username
            space.display_name = f'{space.name} · от {owner}'

    return {
        'available_spaces': spaces,
        'current_space_role': role,
        'current_space_can_edit': can_edit_space(role),
        'current_space_is_owner': is_space_owner(role),
    }


def last_period_summaries(request):
    """Список статей последнего существующего периода в текущем space.

    Доступен глобально через {{ last_period_summaries }} и используется в
    модалке создания нового периода для выбора статей-источников копирования.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    core = getattr(user, 'core_settings', None)
    if not core or not core.current_space:
        return {}

    last = (
        Summary.objects
        .filter(space=core.current_space)
        .values('period_month', 'period_year')
        .order_by('-period_year', '-period_month')
        .first()
    )
    if not last:
        return {'last_period_summaries': [], 'last_period_label': None}

    summaries = list(
        Summary.objects.filter(
            space=core.current_space,
            period_month=last['period_month'],
            period_year=last['period_year'],
        ).order_by('type_transaction', 'group_name')
    )

    months = [
        '', 'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
        'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь',
    ]
    label = f"{months[last['period_month']]} {last['period_year']}"

    return {
        'last_period_summaries': summaries,
        'last_period_label': label,
    }
