from .models import Summary


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
