from django.conf import settings
from django.db.models import QuerySet
from openpyxl import Workbook


def export_transactions_to_excel(transactions: QuerySet) -> Workbook:
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
