from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from users.models import User
from .serializers import TransactionSerializer


class TransactionViewSet(ModelViewSet):
    """CRUD for transactions."""

    serializer_class = TransactionSerializer

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return self.get_user().transactions

    def perform_create(self, serializer):
        user = self.get_user()
        serializer.save(
            author=user,
            basename=user.core_settings.current_basename
        )