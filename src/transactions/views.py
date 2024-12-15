from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from .models import Summary


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
        income_plan = summary.filter(
            type_transaction='income'
        ).aggregate(Sum('plan_value'))['plan_value__sum'] or Decimal('0.0')
        income_fact = summary.filter(
            type_transaction='income'
        ).aggregate(Sum('fact_value'))['fact_value__sum'] or Decimal('0.0')
        expense_plan = summary.filter(
            type_transaction='expense'
        ).aggregate(Sum('plan_value'))['plan_value__sum'] or Decimal('0.0')
        expense_fact = summary.filter(
            type_transaction='expense'
        ).aggregate(Sum('fact_value'))['fact_value__sum'] or Decimal('0.0')
        context.update(
            {
                'title': 'FF',
                'incomes': summary.filter(
                    type_transaction='income'
                ),
                'expenses': summary.filter(
                    type_transaction='expense'
                ),
                'sum_income_plan': income_plan,
                'sum_income_fact': income_fact,
                'sum_expense_plan': expense_plan,
                'sum_expense_fact': expense_fact,
                'balance_plan': income_plan - expense_plan,
                'balance_fact': income_fact - expense_fact,
                'current_month': current_month,
                'current_year': current_year,
                'current_space': current_space
            }
        )
        return context
