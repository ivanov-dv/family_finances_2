from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.viewsets import GenericViewSet

from export.services import create_export_excel_transactions_response

User = get_user_model()


class ExportView(GenericViewSet):

    @action(methods=['GET'], detail=False, url_path='excel')
    def excel(self, request, user_id):
        """Экспорт в excel."""

        # Получаем пользователя.
        user = User.objects.filter(id=user_id).first()

        # Если пользователь не существует, ошибка 404.
        if not user:
            raise NotFound('Пользователь не существует.')

        return create_export_excel_transactions_response(user)
