from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from tools.transactions import get_summary_report
from .models import Summary, Transaction


class HomePageView(TemplateView):
    template_name = 'transactions/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'FF'
        return context


class SummaryView(LoginRequiredMixin, TemplateView):
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
                'title': 'FF',
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
                'current_space': current_space
            }
        )
        return context


class TransactionView(LoginRequiredMixin, TemplateView):
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
                'title': 'FF',
                'transactions': transactions,
                'current_month': current_month,
                'current_year': current_year,
                'current_space': current_space
            }
        )
        return context
