from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction as db_transaction
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from family_finances.constants import MONTH_NAMES
from tools.transactions import get_summary_report
from .amounts import MAX_AMOUNT, AmountError, parse_amount
from .models import Space, Summary, Transaction
from .permissions import CurrentSpaceEditMixin, get_space_role, can_edit_space
from .exceptions import PeriodError, SpaceError
from .services import PeriodService, SpaceService, SummaryService
from .text import clean_text


def get_safe_next_url(request):
    """Безопасный next_url из POST/GET (защита от open redirect)."""
    next_url = request.POST.get('next') or request.GET.get('next') or '/'
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return '/'
    return next_url


class HomePageView(TemplateView):
    template_name = 'transactions/index.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('transactions:summary')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = settings.PROJECT_TITLE
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'core_settings'):
            context.update(
                {
                    'current_month': user.core_settings.current_month,
                    'current_year': user.core_settings.current_year,
                    'current_space': user.core_settings.current_space,
                    'next': self.request.path,
                }
            )
        return context


def _by_name(summary: Summary) -> tuple[str, int]:
    """Ключ порядка статей: название без учёта регистра. Сортировка в Python, а не в БД: lower() в SQLite
    не понижает регистр кириллицы, и порядок зависел бы от СУБД."""
    return summary.group_name.casefold(), summary.pk


class SummaryView(LoginRequiredMixin, TemplateView):
    """Отчет по периоду."""

    template_name = 'transactions/summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_month = self.request.user.core_settings.current_month
        current_year = self.request.user.core_settings.current_year
        current_space = self.request.user.core_settings.current_space
        summary = Summary.objects.filter(
            period_month=current_month,
            period_year=current_year,
            space=current_space
        )
        summary_report = get_summary_report(summary)
        # По названию, а не по времени правки (порядок модели): иначе статья «прыгает» наверх после каждой операции.
        incomes = sorted(summary.filter(type_transaction='income'), key=_by_name)
        expenses = sorted(summary.filter(type_transaction='expense'), key=_by_name)
        balance_plan = summary_report.income_plan - summary_report.expense_plan
        balance_fact = summary_report.income_fact - summary_report.expense_fact
        expense_ratio = (
            round(summary_report.expense_fact / summary_report.expense_plan * 100)
            if summary_report.expense_plan else 0
        )
        context.update(
            {
                'title': settings.PROJECT_TITLE,
                'incomes': incomes,
                'expenses': expenses,
                'sum_income_plan': summary_report.income_plan,
                'sum_income_fact': summary_report.income_fact,
                'sum_expense_plan': summary_report.expense_plan,
                'sum_expense_fact': summary_report.expense_fact,
                'balance_plan': balance_plan,
                'balance_fact': balance_fact,
                'income_delta': summary_report.income_fact - summary_report.income_plan,
                'expense_delta': summary_report.expense_fact - summary_report.expense_plan,
                'balance_delta': balance_fact - balance_plan,
                'expense_ratio': expense_ratio,
                'incomes_json': [
                    {'g': i.group_name, 'plan': float(i.plan_value), 'fact': float(i.fact_value)}
                    for i in incomes
                ],
                'expenses_json': [
                    {'g': e.group_name, 'plan': float(e.plan_value), 'fact': float(e.fact_value)}
                    for e in expenses
                ],
                'current_month': current_month,
                'current_year': current_year,
                'current_space': current_space,
                'next': self.request.path,
            }
        )
        return context


class TransactionView(LoginRequiredMixin, TemplateView):
    """Отчет по транзакциям за период."""

    template_name = 'transactions/transactions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_month = self.request.user.core_settings.current_month
        current_year = self.request.user.core_settings.current_year
        current_space = self.request.user.core_settings.current_space
        transactions = list(Transaction.objects.filter(
            space=current_space,
            period_month=current_month,
            period_year=current_year
        ).select_related('author'))
        # Статью могли удалить: её операции остаются в журнале (связь по совпадению полей), но в отчёт не попадают.
        # Помечаем такие операции, чтобы расхождение журнала и дашборда не выглядело потерей данных.
        existing = set(Summary.objects.filter(
            space=current_space, period_month=current_month, period_year=current_year,
        ).values_list('type_transaction', 'group_name'))
        for tx in transactions:
            tx.orphan = (tx.type_transaction, tx.group_name) not in existing
        context.update(
            {
                'title': settings.PROJECT_TITLE,
                'transactions': transactions,
                'group_names': sorted({tx.group_name for tx in transactions}, key=str.casefold),
                'current_month': current_month,
                'current_year': current_year,
                'current_space': current_space,
                'next': self.request.path,
            }
        )
        return context


class ChangePeriod(LoginRequiredMixin, TemplateView):
    template_name = 'transactions/change_period.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        core = self.request.user.core_settings
        periods = (
            Summary.objects
            .filter(space=core.current_space)
            .values_list('period_year', 'period_month')
            .distinct()
            .order_by('-period_year', '-period_month')
        )
        context.update({
            'title': settings.PROJECT_TITLE,
            'periods': [
                {
                    'key': f'{year}_{month}',
                    'label': f'{MONTH_NAMES[month - 1]} {year}',
                    'is_current': (year, month) == (core.current_year, core.current_month),
                }
                for year, month in periods
                if 1 <= month <= 12
            ],
            'current_month': core.current_month,
            'current_year': core.current_year,
            'current_space': core.current_space,
            'next': self.request.GET.get('next', '/'),
        })
        return context


class AddTransactionView(LoginRequiredMixin, CurrentSpaceEditMixin, TemplateView):
    """Форма добавления транзакции."""

    template_name = 'transactions/add_transaction.html'

    def _get_groups(self, user, type_transaction):
        return list(
            Summary.objects.filter(
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year,
                type_transaction=type_transaction,
            ).values_list('group_name', flat=True).order_by('group_name')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({
            'title': settings.PROJECT_TITLE,
            'income_groups': self._get_groups(user, 'income'),
            'expense_groups': self._get_groups(user, 'expense'),
            'current_month': user.core_settings.current_month,
            'current_year': user.core_settings.current_year,
            'current_space': user.core_settings.current_space,
            'next': self.request.path,
        })
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        type_transaction = request.POST.get('type_transaction', '').strip()
        group_name = clean_text(request.POST.get('group_name', ''))
        description = clean_text(request.POST.get('description', ''))

        if type_transaction not in ('income', 'expense'):
            messages.error(request, 'Неверный тип транзакции.')
            return redirect('transactions:add_transaction')

        if not group_name:
            messages.error(request, 'Необходимо выбрать статью.')
            return redirect('transactions:add_transaction')

        try:
            value = parse_amount(request.POST.get('value_transaction', ''), allow_negative=True)
        except AmountError as e:
            messages.error(request, str(e))
            return redirect('transactions:add_transaction')

        current_space = user.core_settings.current_space
        current_month = user.core_settings.current_month
        current_year = user.core_settings.current_year

        with db_transaction.atomic():
            # Блокировка строки статьи: иначе параллельные добавления перезаписывают
            # fact_value друг друга (read-modify-write) и факт расходится с суммой операций.
            summary = Summary.objects.select_for_update().filter(
                space=current_space,
                period_month=current_month,
                period_year=current_year,
                type_transaction=type_transaction,
                group_name=group_name,
            ).first()

            if not summary:
                messages.error(request, f'Статья «{group_name}» не найдена в текущем периоде.')
                return redirect('transactions:add_transaction')

            new_fact = summary.fact_value + value
            if abs(new_fact) > MAX_AMOUNT:
                messages.error(request, 'Итог по статье превысит допустимое значение.')
                return redirect('transactions:add_transaction')

            Transaction.objects.create(
                author=user,
                space=current_space,
                period_month=current_month,
                period_year=current_year,
                type_transaction=type_transaction,
                group_name=group_name,
                description=description,
                value_transaction=value,
            )
            summary.fact_value = new_fact
            summary.save(update_fields=['fact_value', 'updated_at'])

        messages.success(request, 'Транзакция добавлена.')
        return redirect('transactions:add_transaction')


class AddSummaryView(LoginRequiredMixin, CurrentSpaceEditMixin, TemplateView):
    """Форма создания статьи (группы) в сводке текущего периода."""

    template_name = 'transactions/add_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        core = user.core_settings
        summaries = list(
            Summary.objects.filter(
                space=core.current_space,
                period_month=core.current_month,
                period_year=core.current_year,
            ).order_by('type_transaction', 'group_name')
        )
        # Операции не привязаны к статье внешним ключом и переживают её удаление —
        # число операций нужно, чтобы предупредить об этом в подтверждении удаления.
        stats = SummaryService.transaction_stats(core.current_space, core.current_month, core.current_year)
        for summary in summaries:
            summary.tx_count = stats.get((summary.type_transaction, summary.group_name), {}).get('count', 0)
        context.update({
            'title': settings.PROJECT_TITLE,
            'summaries': summaries,
            'current_month': user.core_settings.current_month,
            'current_year': user.core_settings.current_year,
            'current_space': user.core_settings.current_space,
            'next': self.request.path,
        })
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        type_transaction = request.POST.get('type_transaction', '').strip()
        group_name = clean_text(request.POST.get('group_name', ''))

        if type_transaction not in ('income', 'expense'):
            messages.error(request, 'Неверный тип статьи.')
            return redirect('transactions:add_summary')

        if not group_name:
            messages.error(request, 'Введите название статьи.')
            return redirect('transactions:add_summary')

        if len(group_name) > 30:
            messages.error(request, 'Название статьи не должно превышать 30 символов.')
            return redirect('transactions:add_summary')

        try:
            plan_value = parse_amount(request.POST.get('plan_value', ''), allow_zero=True)
        except AmountError as e:
            if e.code == 'too_large':
                messages.error(request, str(e))
            else:
                messages.error(request, 'Введите корректное плановое значение (не менее 0).')
            return redirect('transactions:add_summary')

        core = user.core_settings
        # Статья могла быть удалена раньше, а её операции остались: факт берём из них.
        existing = SummaryService.transaction_stats(
            core.current_space, core.current_month, core.current_year
        ).get((type_transaction, group_name))
        try:
            Summary.objects.create(
                space=core.current_space,
                period_month=core.current_month,
                period_year=core.current_year,
                type_transaction=type_transaction,
                group_name=group_name,
                plan_value=plan_value,
                fact_value=existing['total'] if existing else Decimal('0'),
            )
        except IntegrityError:
            messages.error(request, f'Статья «{group_name}» уже существует в текущем периоде.')
            return redirect('transactions:add_summary')

        messages.success(request, f'Статья «{group_name}» создана.')
        return redirect('transactions:add_summary')


@login_required
def delete_summary(request, pk):
    """Удаление статьи текущего пользователя."""
    if request.method != 'POST':
        return redirect('transactions:add_summary')
    role = get_space_role(request.user, request.user.core_settings.current_space)
    if not can_edit_space(role):
        messages.error(request, 'Недостаточно прав для изменения данного пространства.')
        return redirect('transactions:add_summary')
    summary = Summary.objects.filter(
        pk=pk,
        space=request.user.core_settings.current_space,
    ).first()
    if not summary:
        messages.error(request, 'Статья не найдена или недоступна.')
    else:
        name = summary.group_name
        summary.delete()
        messages.success(request, f'Статья «{name}» удалена.')
    return redirect('transactions:add_summary')


class SpaceActionView(LoginRequiredMixin, View):
    """База POST-вьюх управления пространствами.

    Валидирует next_url, ловит SpaceError → messages.error,
    success-сообщение из perform() → messages.success, редиректит на next.
    Сабкласс реализует perform() с бизнес-логикой.
    """

    def post(self, request, *args, **kwargs):
        next_url = get_safe_next_url(request)
        try:
            message = self.perform(request, *args, **kwargs)
            if message:
                messages.success(request, message)
        except SpaceError as e:
            messages.error(request, str(e))
        return redirect(next_url)

    def perform(self, request, *args, **kwargs) -> str | None:
        """Выполнить операцию. Вернуть success-сообщение либо None."""
        raise NotImplementedError

    @staticmethod
    def _get_owned_space(request, pk: int) -> Space:
        space = Space.objects.filter(pk=pk, user=request.user).first()
        if not space:
            raise SpaceError('Пространство не найдено.')
        return space


class ApplySpaceView(SpaceActionView):
    """Переключение активного пространства."""

    def perform(self, request, *args, **kwargs):
        # Нечисловой id из подменённой формы — «не найдено», а не ValueError/500.
        try:
            space_id = int(request.POST.get('space'))
        except (TypeError, ValueError):
            raise SpaceError('Пространство не найдено.')
        space = Space.objects.filter(pk=space_id).first() if 0 < space_id < 2 ** 63 else None
        if not space:
            raise SpaceError('Пространство не найдено.')
        SpaceService.apply_space(request.user, space)


class LeaveSpaceView(SpaceActionView):
    """Участник покидает пространство."""

    def perform(self, request, pk, *args, **kwargs):
        space = Space.objects.filter(pk=pk).first()
        if not space:
            raise SpaceError('Пространство не найдено.')
        SpaceService.leave_space(request.user, space)
        return f'Вы покинули пространство «{space.name}».'


class CreateSpaceView(SpaceActionView):
    """Создание нового пространства."""

    def perform(self, request, *args, **kwargs):
        space = SpaceService.create_space(request.user, request.POST.get('name', ''))
        return f'Пространство «{space.name}» создано.'


class RenameSpaceView(SpaceActionView):
    """Переименование пространства владельцем."""

    def perform(self, request, pk, *args, **kwargs):
        space = self._get_owned_space(request, pk)
        SpaceService.rename_space(space, request.POST.get('name', ''))
        return f'Пространство переименовано в «{space.name}».'


class DeleteSpaceView(SpaceActionView):
    """Удаление пространства владельцем."""

    def perform(self, request, pk, *args, **kwargs):
        space = self._get_owned_space(request, pk)
        SpaceService.delete_space(space, request.user)
        return 'Пространство удалено.'


class InviteUserView(SpaceActionView):
    """Приглашение участника владельцем."""

    def perform(self, request, pk, *args, **kwargs):
        space = self._get_owned_space(request, pk)
        target = SpaceService.invite_user(
            space, request.POST.get('username', ''), request.POST.get('role', ''),
        )
        return f'Пользователь «{target.username}» приглашён.'


class ChangeMemberRoleView(SpaceActionView):
    """Смена роли участника владельцем."""

    def perform(self, request, pk, *args, **kwargs):
        space = self._get_owned_space(request, pk)
        SpaceService.change_member_role(
            space, request.POST.get('linked_user_id'), request.POST.get('role', ''),
        )
        return 'Роль участника обновлена.'


class RemoveMemberView(SpaceActionView):
    """Исключение участника владельцем."""

    def perform(self, request, pk, *args, **kwargs):
        space = self._get_owned_space(request, pk)
        SpaceService.remove_member(space, request.POST.get('linked_user_id'))
        return 'Участник исключён.'


@login_required
def apply_period(request):
    """Применение смены периода и редирект на предыдущую страницу."""
    next_url = get_safe_next_url(request)
    try:
        PeriodService.apply_period(request.user, request.GET.get('period'))
    except PeriodError as e:
        messages.error(request, str(e))
    return redirect(next_url)


@login_required
def create_period(request):
    """Создание нового периода с автокопированием статей из последнего."""
    if request.method != 'POST':
        return redirect('transactions:change_period')

    next_url = get_safe_next_url(request)

    try:
        period_month = int(request.POST.get('period_month', ''))
        period_year = int(request.POST.get('period_year', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Некорректный месяц или год.')
        return redirect(next_url)

    # Снятые флажки браузер не отправляет: форма со списком статей шлёт маркер copy_selection,
    # чтобы пустой набор означал «ничего не копировать», а не «копировать всё».
    selected_ids = None
    if request.POST.get('copy_selection') or 'copy_summary_ids' in request.POST:
        try:
            selected_ids = {int(pk) for pk in request.POST.getlist('copy_summary_ids') if pk}
        except ValueError:
            selected_ids = set()

    plan_overrides = {}
    for key in request.POST:
        if key.startswith('plan_value_'):
            try:
                plan_overrides[int(key[len('plan_value_'):])] = request.POST[key]
            except ValueError:
                pass

    try:
        result = PeriodService.create_period(
            request.user, period_month, period_year, selected_ids, plan_overrides,
        )
    except PeriodError as e:
        messages.error(request, str(e))
        return redirect(next_url)

    if result.already_exists:
        messages.info(request, 'Этот период уже существует — переключились на него.')
    elif result.copied_count:
        messages.success(request, f'Период создан · скопировано статей: {result.copied_count}.')
    else:
        messages.info(request, 'Период создан. Добавьте статьи бюджета на странице «Статьи».')

    return redirect(next_url)
