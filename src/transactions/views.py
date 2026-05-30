from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction as db_transaction
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from tools.transactions import get_summary_report
from .models import Space, Summary, Transaction
from .permissions import CurrentSpaceEditMixin, get_space_role, can_edit_space
from .exceptions import PeriodError, SpaceError
from .services import PeriodService, SpaceService


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
        incomes = summary.filter(type_transaction='income')
        expenses = summary.filter(type_transaction='expense')
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
        transactions = Transaction.objects.filter(
            space=self.request.user.core_settings.current_space,
            period_month=self.request.user.core_settings.current_month,
            period_year=self.request.user.core_settings.current_year
        )
        context.update(
            {
                'title': settings.PROJECT_TITLE,
                'transactions': transactions,
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
        periods = Summary.objects.filter(
            space=self.request.user.core_settings.current_space
        ).values('period_month', 'period_year')
        sorted_unique_periods = sorted(
            {f'{period["period_year"]}_{period['period_month']}' for period in periods},
            reverse=True
        )
        context.update({
            'title': settings.PROJECT_TITLE,
            'periods': sorted_unique_periods,
            'current_month': self.request.user.core_settings.current_month,
            'current_year': self.request.user.core_settings.current_year,
            'current_space': self.request.user.core_settings.current_space,
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
        group_name = request.POST.get('group_name', '').strip()
        description = request.POST.get('description', '').strip()
        value_raw = request.POST.get('value_transaction', '').strip()

        if type_transaction not in ('income', 'expense'):
            messages.error(request, 'Неверный тип транзакции.')
            return redirect('transactions:add_transaction')

        if not group_name:
            messages.error(request, 'Необходимо выбрать статью.')
            return redirect('transactions:add_transaction')

        try:
            value = Decimal(value_raw.replace(',', '.'))
            if value == 0:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, 'Введите корректную сумму (не равную нулю).')
            return redirect('transactions:add_transaction')

        current_space = user.core_settings.current_space
        current_month = user.core_settings.current_month
        current_year = user.core_settings.current_year

        summary = Summary.objects.filter(
            space=current_space,
            period_month=current_month,
            period_year=current_year,
            type_transaction=type_transaction,
            group_name=group_name,
        ).first()

        if not summary:
            messages.error(request, f'Статья «{group_name}» не найдена в текущем периоде.')
            return redirect('transactions:add_transaction')

        with db_transaction.atomic():
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
            summary.fact_value += value
            summary.save()

        messages.success(request, 'Транзакция добавлена.')
        return redirect('transactions:add_transaction')


class AddSummaryView(LoginRequiredMixin, CurrentSpaceEditMixin, TemplateView):
    """Форма создания статьи (группы) в сводке текущего периода."""

    template_name = 'transactions/add_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        summaries = Summary.objects.filter(
            space=user.core_settings.current_space,
            period_month=user.core_settings.current_month,
            period_year=user.core_settings.current_year,
        ).order_by('type_transaction', 'group_name')
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
        group_name = request.POST.get('group_name', '').strip()
        plan_raw = request.POST.get('plan_value', '').strip()

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
            plan_value = Decimal(plan_raw.replace(',', '.')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if plan_value < 0:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, 'Введите корректное плановое значение (не менее 0).')
            return redirect('transactions:add_summary')

        try:
            Summary.objects.create(
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year,
                type_transaction=type_transaction,
                group_name=group_name,
                plan_value=plan_value,
            )
        except IntegrityError:
            messages.error(
                request,
                f'Статья «{group_name}» уже существует в текущем периоде для этого типа.'
            )
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
        space = Space.objects.filter(pk=request.POST.get('space')).first()
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

    selected_ids = None
    if 'copy_summary_ids' in request.POST:
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
