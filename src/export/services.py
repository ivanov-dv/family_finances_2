from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from transactions.models import Transaction

User = get_user_model()

DATE_FORMAT = 'DD.MM.YYYY'

# Строка, начинающаяся с этих символов, при правке в Excel превращается в формулу.
_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def _text(value) -> str:
    """Пользовательская строка без символов, недопустимых в XML (иначе openpyxl падает с 500)."""
    return ILLEGAL_CHARACTERS_RE.sub('', str(value or ''))


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
        # Дата — в часовом поясе приложения (как в интерфейсе), а не в UTC.
        created_at = timezone.localtime(transaction.created_at)
        row = [
            created_at.date(),
            'Доход' if transaction.type_transaction == 'income' else 'Расход',
            _text(transaction.group_name),
            transaction.value_transaction,
            _text(transaction.description),
            _text(transaction.author.username)
        ]
        ws.append(row)
        row_number = ws.max_row
        ws.cell(row_number, 1).number_format = DATE_FORMAT
        # Пользовательский текст всегда остаётся строкой: значение «=1+1» иначе
        # записывается в файл как формула и вычисляется при открытии.
        for column in (3, 5, 6):
            cell = ws.cell(row_number, column)
            cell.data_type = 's'
            if cell.value.startswith(_FORMULA_PREFIXES):
                cell.quotePrefix = True

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
    ).select_related('author')

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
