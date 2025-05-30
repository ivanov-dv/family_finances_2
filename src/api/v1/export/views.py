from django.contrib.auth import get_user_model
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from export.services import create_export_excel_transactions_response

User = get_user_model()


class ExportAPIView(APIView):
    """Экспорт данных в Excel."""

    @swagger_auto_schema(
        operation_description='Запрос транзакций пользователя в текущем периоде в Excel',
        responses={200: openapi.Response('Файл отправлен')}
    )
    def get(self, request, user_id):
        """Экспорт в excel."""

        # Получаем пользователя.
        user = User.objects.filter(id=user_id).first()

        # Если пользователь не существует, ошибка 404.
        if not user:
            raise NotFound('Пользователь не существует.')

        return create_export_excel_transactions_response(user)
