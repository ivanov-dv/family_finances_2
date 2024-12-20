from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet

from export.services import create_excel_workbook
from transactions.models import Transaction

User = get_user_model()


class ExportView(GenericViewSet):

    @action(methods=['GET'], detail=False, url_path='excel')
    def excel(self, request, user_id):
        """Экспорт в excel."""

        # Получаем пользователя.
        user = User.objects.filter(id=user_id).first()

        # Получаем транзакции текущего периода.
        transactions = Transaction.objects.filter(
            space=user.core_settings.current_space,
            period_month=user.core_settings.current_month,
            period_year=user.core_settings.current_year
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
            'attachment;'
            f' filename={settings.TRANSACTIONS_EXPORT_EXCEL_FILENAME}'
        )

        # Сохранение таблицы в ответе.
        workbook.save(response)

        return response
