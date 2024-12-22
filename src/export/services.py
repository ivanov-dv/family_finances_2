from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.http import HttpResponse
from openpyxl import Workbook

from transactions.models import Transaction

User = get_user_model()


def _create_excel_transactions_workbook(transactions: QuerySet) -> Workbook:
    """
    Экспортирует транзакции в Excel-файл.

    :param transactions: QuerySet с транзакциями.
    :return: Workbook с экспортированными данными.
    """

    # Создание Workbook и активной страницы.
    wb = Workbook()
    ws = wb.active

    # Установка названия листа.
    ws.title = settings.TRANSACTIONS_EXPORT_EXCEL_SHEET_NAME

    # Заполнение заголовка.
    headers = ['Дата', 'Тип', 'Статья', 'Значение', 'Описание', 'Автор']
    ws.append(headers)

    # Заполнение транзакций.
    for transaction in transactions:
        row = [
            transaction.created_at.strftime('%d.%m.%Y'),
            'Доход' if transaction.type_transaction == 'income' else 'Расход',
            transaction.group_name,
            transaction.value_transaction,
            transaction.description,
            transaction.author.username
        ]
        ws.append(row)

    # Установка ширины столбцов.
    ws.column_dimensions['A'].width = settings.COL_WIDTH_DATE
    ws.column_dimensions['B'].width = settings.COL_WIDTH_TYPE_TRANSACTION
    ws.column_dimensions['C'].width = settings.COL_WIDTH_GROUP
    ws.column_dimensions['D'].width = settings.COL_WIDTH_VALUE_TRANSACTION
    ws.column_dimensions['E'].width = settings.COL_WIDTH_DESCRIPTION
    ws.column_dimensions['F'].width = settings.COL_WIDTH_AUTHOR

    return wb


def create_export_excel_transactions_response(user: User) -> HttpResponse:
    """
    Создает ответ (response) с экспортированными транзакциями в Excel.
    Период и Space для фильтрации извлекается из core_settings пользователя.

    :param user: Пользователь.
    :return: HttpResponse с экспортированными транзакциями в Excel.
    """

    # Получаем транзакции текущего периода.
    transactions = Transaction.objects.filter(
        space=user.core_settings.current_space,
        period_month=user.core_settings.current_month,
        period_year=user.core_settings.current_year
    )

    # Экспортируем транзакции в Excel и получаем таблицу.
    workbook = _create_excel_transactions_workbook(transactions)

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
