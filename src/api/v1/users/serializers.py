from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    linked_users = serializers.SlugRelatedField(
        required=False,
        queryset=User.objects.all(),
        many=True,
        slug_field='username'
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=(validate_password,)
    )

    class Meta:
        fields = (
            'id',
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'id_telegram',
            'telegram_only',
            'date_joined',
            'last_login',
            'linked_users'
        )
        model = User

    def validate_telegram_only(self, telegram_only):
        id_telegram = self.initial_data.get('id_telegram')
        password = self.initial_data.get('password')
        if telegram_only is True and not id_telegram:
            raise serializers.ValidationError(
                {'id_telegram': 'This field is required, '
                                'if field telegram_only is True'}
            )
        if telegram_only is False and not password:
            raise serializers.ValidationError(
                {'password': 'This field is required, '
                             'if field telegram_only is False'}
            )
        return telegram_only
