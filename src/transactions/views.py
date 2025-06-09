from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from tools.transactions import get_summary_report
from .models import Summary, Transaction


class HomePageView(TemplateView):
    template_name = 'transactions/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = settings.PROJECT_TITLE
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
        context.update(
            {
                'title': settings.PROJECT_TITLE,
                'incomes': summary.filter(type_transaction='income'),
                'expenses': summary.filter(type_transaction='expense'),
                'sum_income_plan': summary_report.income_plan,
                'sum_income_fact': summary_report.income_fact,
                'sum_expense_plan': summary_report.expense_plan,
                'sum_expense_fact': summary_report.expense_fact,
                'balance_plan':
                    summary_report.income_plan - summary_report.expense_plan,
                'balance_fact':
                    summary_report.income_fact - summary_report.expense_fact,
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
        context.update({'periods': sorted_unique_periods, 'next': self.request.GET.get('next', '/')})
        return context


@login_required
def apply_period(request):
    """Применение смены периода и редирект на предыдущую страницу."""
    period = request.GET.get('period')
    next_url = request.GET.get('next', '/')

    if period:
        year, month = map(int, period.split('_'))
        request.user.core_settings.current_year = year
        request.user.core_settings.current_month = month
        request.user.core_settings.save()

    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = '/'

    return redirect(next_url)
