import pytest
from django.urls import reverse
from openpyxl.workbook import Workbook

from export.services import _create_excel_transactions_workbook
from transactions.models import Transaction

pytestmark = pytest.mark.django_db(transaction=True)


class TestExport:

    url = reverse('export:excel')

    def test_create_excel_workbook(self, user_2_tg_only, many_transactions):
        transactions = Transaction.objects.filter(
            space=user_2_tg_only.core_settings.current_space,
            period_month=user_2_tg_only.core_settings.current_month,
            period_year=user_2_tg_only.core_settings.current_year
        )
        workbook = _create_excel_transactions_workbook(transactions)
        assert isinstance(workbook, Workbook)

    def test_export_excel_view(self, user_1_client):
        response = user_1_client.get(self.url)
        assert response.status_code == 200
        assert (response['Content-Type'] ==
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet')
        assert 'Content-Disposition' in response
        assert 'attachment; filename=' in response['Content-Disposition']
        assert 'xlsx' in response['Content-Disposition']
