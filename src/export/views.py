from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from export.services import create_excel_workbook
from transactions.models import Transaction


@login_required
def export_excel(request):
    """Экспорт в excel."""

    # Получаем транзакции текущего периода.
    transactions = Transaction.objects.filter(
        space=request.user.core_settings.current_space,
        period_month=request.user.core_settings.current_month,
        period_year=request.user.core_settings.current_year
    )

    # Экспортируем транзакции в Excel и получаем таблицу.
    workbook = create_excel_workbook(transactions)

    # Установка типа контента.
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.'
                     'spreadsheetml.sheet'
    )

    # Установка заголовка для сохранения файла.
    response['Content-Disposition'] = (
        f'attachment; filename={settings.TRANSACTIONS_EXPORT_EXCEL_FILENAME}'
    )

    # Сохранение таблицы в ответе.
    workbook.save(response)

    return response
