from rest_framework.viewsets import ModelViewSet

from api.v1.users.serializers import UserSerializer
from users.models import User


class UserViewSet(ModelViewSet):
    """CRUD for users."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

