from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction as db_transaction

from users.models import User

from .dto import PeriodCreateResult
from .exceptions import PeriodError, SpaceError
from .models import LinkedUserToSpace, Space, Summary
from .permissions import can_edit_space, get_space_role


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

    @staticmethod
    def _validate_role(role: str) -> str:
        """Проверить, что роль входит в допустимые. Вернуть её либо кинуть SpaceError."""
        if role not in dict(LinkedUserToSpace.ROLE_CHOICES):
            raise SpaceError('Недопустимая роль.')
        return role

    @staticmethod
    def invite_user(space: Space, username: str, role: str) -> User:
        """Пригласить существующего юзера по логину с ролью. Вернуть приглашённого."""
        role = SpaceService._validate_role(role)
        target = User.objects.filter(username=username.strip().lower()).first()
        if not target:
            raise SpaceError('Пользователь с таким логином не найден.')
        if target.id == space.user_id:
            raise SpaceError('Нельзя пригласить владельца пространства.')
        if LinkedUserToSpace.objects.filter(space=space, linked_user=target).exists():
            raise SpaceError('Пользователь уже является участником.')
        LinkedUserToSpace.objects.create(space=space, linked_user=target, role=role)
        return target

    @staticmethod
    def change_member_role(space: Space, linked_user_id: int | str, role: str) -> None:
        """Сменить роль участника пространства."""
        role = SpaceService._validate_role(role)
        link = LinkedUserToSpace.objects.filter(
            space=space, linked_user_id=linked_user_id,
        ).first()
        if not link:
            raise SpaceError('Участник не найден.')
        link.role = role
        link.save()

    @staticmethod
    def remove_member(space: Space, linked_user_id: int | str) -> None:
        """Исключить участника. Если space был его current_space — сбросить в None."""
        link = LinkedUserToSpace.objects.filter(
            space=space, linked_user_id=linked_user_id,
        ).first()
        if not link:
            raise SpaceError('Участник не найден.')
        member = link.linked_user
        cs = getattr(member, 'core_settings', None)
        if cs and cs.current_space_id == space.id:
            cs.current_space = None
            cs.save()
        link.delete()


class PeriodService:
    """Бизнес-логика операций с периодом (current_month/current_year)."""

    @staticmethod
    def apply_period(user: User, period: str | None) -> None:
        """Переключить текущий период пользователя. period — строка 'YYYY_MM'."""
        if get_space_role(user, user.core_settings.current_space) is None:
            raise PeriodError('Нет доступа к текущему пространству.')
        if not period:
            return
        try:
            year, month = map(int, period.split('_'))
        except (ValueError, AttributeError):
            raise PeriodError('Некорректный период.')
        PeriodService._set_current_period(user, month, year)

    @staticmethod
    def create_period(
        user: User,
        month: int,
        year: int,
        selected_ids: set[int] | None,
        plan_overrides: dict[int, str],
    ) -> PeriodCreateResult:
        """Создать период с автокопированием статей из последнего.

        selected_ids=None — копировать все статьи; иначе только выбранные.
        plan_overrides — переопределения plan_value по id исходной статьи.
        """
        space = user.core_settings.current_space
        if not can_edit_space(get_space_role(user, space)):
            raise PeriodError('Недостаточно прав для изменения данного пространства.')
        if not (1 <= month <= 12) or not (2020 <= year <= 2099):
            raise PeriodError('Месяц должен быть 1–12, год 2020–2099.')

        if Summary.objects.filter(space=space, period_month=month, period_year=year).exists():
            PeriodService._set_current_period(user, month, year)
            return PeriodCreateResult(already_exists=True, copied_count=0)

        copied_count = PeriodService._copy_summaries(
            space, month, year, selected_ids, plan_overrides,
        )
        PeriodService._set_current_period(user, month, year)
        return PeriodCreateResult(already_exists=False, copied_count=copied_count)

    @staticmethod
    def _set_current_period(user: User, month: int, year: int) -> None:
        """Записать текущий период в CoreSettings."""
        user.core_settings.current_month = month
        user.core_settings.current_year = year
        user.core_settings.save()

    @staticmethod
    def _last_period(space: Space) -> dict | None:
        """Самый поздний период пространства ({'period_month', 'period_year'}) либо None."""
        return (
            Summary.objects
            .filter(space=space)
            .values('period_month', 'period_year')
            .order_by('-period_year', '-period_month')
            .first()
        )

    @staticmethod
    def _resolve_plan_value(summary: Summary, plan_overrides: dict[int, str]) -> Decimal:
        """plan_value для копии: переопределение из формы либо исходное значение."""
        raw = (plan_overrides.get(summary.pk) or '').strip().replace(',', '.')
        if raw:
            try:
                candidate = Decimal(raw)
                if candidate >= 0:
                    return candidate
            except InvalidOperation:
                pass
        return summary.plan_value

    @staticmethod
    def _copy_summaries(
        space: Space,
        month: int,
        year: int,
        selected_ids: set[int] | None,
        plan_overrides: dict[int, str],
    ) -> int:
        """Скопировать статьи последнего периода в новый. Вернуть число скопированных."""
        last_period = PeriodService._last_period(space)
        if not last_period:
            return 0

        source = Summary.objects.filter(
            space=space,
            period_month=last_period['period_month'],
            period_year=last_period['period_year'],
        )
        if selected_ids is not None:
            source = source.filter(pk__in=selected_ids)

        with db_transaction.atomic():
            new_summaries = [
                Summary(
                    space=space,
                    period_month=month,
                    period_year=year,
                    type_transaction=s.type_transaction,
                    group_name=s.group_name,
                    plan_value=PeriodService._resolve_plan_value(s, plan_overrides),
                    fact_value=Decimal('0'),
                )
                for s in source
            ]
            Summary.objects.bulk_create(new_summaries)
        return len(new_summaries)
