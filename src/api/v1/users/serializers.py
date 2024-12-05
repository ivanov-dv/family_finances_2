from datetime import datetime

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from api.v1.transactions.serializers import BasenameSerializer
from api.v1.transactions.validators import PeriodYearValidator, \
    PeriodMonthValidator
from api.v1.users.validators import not_allowed_username_validator
from transactions.models import Basename
from users.models import User, TelegramSettings, CoreSettings


class TelegramSettingsSerializer(serializers.ModelSerializer):
    joint_chat = serializers.CharField(
        required=False
    )
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )

    class Meta:
        model = TelegramSettings
        fields = (
            'user',
            'id_telegram',
            'telegram_only',
            'joint_chat'
        )


class CoreSettingsSerializer(serializers.ModelSerializer):
    current_basename = BasenameSerializer(
        read_only=True
    )
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    current_year = serializers.IntegerField(
        validators=(PeriodYearValidator(),)
    )
    current_month = serializers.IntegerField(
        validators=(PeriodMonthValidator(),)
    )

    class Meta:
        model = CoreSettings
        fields = (
            'user',
            'current_basename',
            'current_month',
            'current_year'
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

    class Meta:
        fields = (
            'id',
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'telegram_only',
            'id_telegram'
        )
        model = User

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        telegram_only = validated_data.pop('telegram_only', None)
        id_telegram = validated_data.pop('id_telegram', None)
        validated_data['username'] = validated_data['username'].lower()
        with transaction.atomic():
            user = User.objects.create(**validated_data)
            if password:
                user.set_password(password)
                user.save()
            TelegramSettings.objects.create(
                user=user,
                telegram_only=telegram_only,
                id_telegram=id_telegram
            )
            basename = Basename.objects.create(
                user=user,
                basename=user.username
            )
            dt = datetime.now()
            CoreSettings.objects.create(
                user=user,
                current_basename=basename,
                current_month=dt.month,
                current_year=dt.year
            )
            return user

    def validate_username(self, username):
        return not_allowed_username_validator(username)

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
    core_settings = CoreSettingsSerializer(read_only=True)
    linked_users = serializers.SlugRelatedField(
        read_only=True,
        many=True,
        slug_field='username'
    )
    basenames = BasenameSerializer(read_only=True, many=True)

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
            'core_settings',
            'telegram_settings',
            'linked_users',
            'basenames'
        )
