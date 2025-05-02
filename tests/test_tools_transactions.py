from datetime import datetime
from decimal import Decimal

import pytest

from tools.transactions import get_summary_report, SummaryReport
from transactions.models import Summary

pytestmark = pytest.mark.django_db(transaction=True)


def test_get_summary_report(user_2_tg_only, many_transactions):
    dt = datetime.now()
    queryset = Summary.objects.filter(
        period_month=dt.month,
        period_year=dt.year,
        space=user_2_tg_only.core_settings.current_space
    )
    summary_report = get_summary_report(queryset)

    assert isinstance(summary_report, SummaryReport)
    assert summary_report.income_plan == Decimal('10')
    assert summary_report.expense_plan == Decimal('10')
    assert summary_report.income_fact == Decimal('10.32')
    assert summary_report.expense_fact == Decimal('10.32')
