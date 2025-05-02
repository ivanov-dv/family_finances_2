from dataclasses import dataclass
from decimal import Decimal

from django.db.models import QuerySet, Sum


@dataclass
class SummaryReport:
    income_plan: Decimal
    income_fact: Decimal
    expense_plan: Decimal
    expense_fact: Decimal


def get_summary_report(summary_queryset: QuerySet) -> SummaryReport:

    income_plan = summary_queryset.filter(
        type_transaction='income'
    ).aggregate(Sum('plan_value'))['plan_value__sum'] or Decimal('0.0')
    income_fact = summary_queryset.filter(
        type_transaction='income'
    ).aggregate(Sum('fact_value'))['fact_value__sum'] or Decimal('0.0')
    expense_plan = summary_queryset.filter(
        type_transaction='expense'
    ).aggregate(Sum('plan_value'))['plan_value__sum'] or Decimal('0.0')
    expense_fact = summary_queryset.filter(
        type_transaction='expense'
    ).aggregate(Sum('fact_value'))['fact_value__sum'] or Decimal('0.0')

    return SummaryReport(
        income_plan=income_plan,
        income_fact=income_fact,
        expense_plan=expense_plan,
        expense_fact=expense_fact,
    )
