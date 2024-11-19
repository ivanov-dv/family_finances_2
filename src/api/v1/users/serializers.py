from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from users.models import User, TelegramSettings


class TelegramSettingsSerializer(serializers.ModelSerializer):
    joint_chat = serializers.CharField(
        required=False
    )

    class Meta:
        model = TelegramSettings
        fields = (
            'id_telegram',
            'telegram_only',
            'joint_chat'
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=(validate_password,)
    )
    telegram_only = serializers.BooleanField(
        write_only=True
    )
    id_telegram = serializers.IntegerField(
        write_only=True,
        required=False,
        validators=(
            UniqueValidator(
                queryset=TelegramSettings.objects.all(),
                message='Пользователь с таким Telegram ID уже существует.'
            ),
        )
    )
    telegram_settings = TelegramSettingsSerializer(read_only=True)

    class Meta:
        fields = (
            'id',
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'last_login',
            'telegram_only',
            'id_telegram',
            'telegram_settings'
        )
        model = User

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        telegram_only = validated_data.pop('telegram_only', None)
        id_telegram = validated_data.pop('id_telegram', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        TelegramSettings.objects.create(
            user=user,
            telegram_only=telegram_only,
            id_telegram=id_telegram
        )
        return user

    def validate(self, data):
        errors = {}
        if data['telegram_only'] is True and not data.get('id_telegram'):
            errors['id_telegram'] = ('This field is required, '
                                     'if telegram_only is True.')
        if data['telegram_only'] is False and not data.get('password'):
            errors['password'] = ('This field is required, '
                                  'if telegram_only is False.')
        if errors:
            raise serializers.ValidationError(errors)
        return data


class UserDetailSerializer(serializers.ModelSerializer):
    telegram_settings = TelegramSettingsSerializer(read_only=True)
    linked_users = serializers.SlugRelatedField(
        read_only=True,
        many=True,
        slug_field='username'
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'last_login',
            'telegram_settings',
            'linked_users'
        )
