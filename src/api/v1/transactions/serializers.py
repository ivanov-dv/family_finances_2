from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from family_finances import constants
from transactions.models import (
    Transaction,
    Summary,
    Basename,
    LinkedUserToBasename
)
from users.models import User
from .validators import PeriodYearValidator, PeriodMonthValidator


class TransactionCreateSerializer(serializers.ModelSerializer):
    type_transaction = serializers.ChoiceField(
        choices=constants.CHOICE_TYPE_TRANSACTION
    )

    class Meta:
        model = Transaction
        fields = (
            'id',
            'type_transaction',
            'group_name',
            'description',
            'value_transaction',
            'author'
        )
        read_only_fields = ('author', 'basename')

    def create(self, validated_data):
        summary = Summary.objects.filter(
            basename=validated_data['basename'],
            period_month=validated_data['period_month'],
            period_year=validated_data['period_year'],
            type_transaction=validated_data['type_transaction'],
            group_name=validated_data['group_name']
        )
        if not summary.exists():
            raise ValidationError(
                {
                    'group_name': f'Статья {validated_data['group_name']} '
                                  f'не найдена.'
                }
            )
        instance = Transaction.objects.create(**validated_data)
        return instance

    def validate(self, attrs):
        return attrs


class TransactionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Transaction


class GroupCreateSerializer(serializers.ModelSerializer):
    basename = serializers.SlugRelatedField(
        queryset=Basename.objects.all(),
        slug_field='basename'
    )
    fact_value = serializers.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2
    )
    period_year = serializers.IntegerField(
        validators=(PeriodYearValidator(),)
    )
    period_month = serializers.IntegerField(
        validators=(PeriodMonthValidator(),)
    )

    class Meta:
        fields = (
            'id',
            'basename',
            'period_month',
            'period_year',
            'type_transaction',
            'group_name',
            'plan_value',
            'fact_value'
        )
        model = Summary
        validators = (
            serializers.UniqueTogetherValidator(
                queryset=Summary.objects.all(),
                fields=(
                    'basename',
                    'period_month',
                    'period_year',
                    'group_name'
                )
            ),
        )


class GroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'basename',
            'period_month',
            'period_year',
            'type_transaction',
            'group_name',
            'plan_value',
            'fact_value'
        )
        model = Summary

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['owner_base_username'] = instance.basename.user.username
        return representation


class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'type_transaction',
            'group_name',
            'plan_value',
            'fact_value',
            'created_at',
            'updated_at'
        )
        model = Summary


class BasenameSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'basename')
        model = Basename


class LinkUserToBasenameSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def validate(self, attrs):
        """Проверка, что пользователь может быть связан с базой."""
        linked_user_id = attrs['id']
        linked_user = User.objects.filter(pk=linked_user_id).first()
        if not linked_user:
            raise serializers.ValidationError(
                f"Пользователь с id {linked_user_id} не найден.")
        owner_user_id = self.context.get('user_id')
        if linked_user_id == owner_user_id:
            raise serializers.ValidationError(
                'Нельзя самого себя подключить к базе.'
            )
        basename_id = self.context.get('basename_id')
        basename = Basename.objects.filter(pk=basename_id).first()
        if not basename:
            raise serializers.ValidationError(
                f'У пользователя id {owner_user_id} '
                f'нет базы с id {basename_id}'
            )
        if basename.user.id != owner_user_id:
            raise serializers.ValidationError(
                f'У пользователя id {owner_user_id} нет базы '
                f'с id {basename.id}.'
            )
        attrs['basename'] = basename
        attrs['linked_user'] = linked_user
        return attrs

    def create(self, validated_data):
        """Подключение пользователя к базе."""
        try:
            linked = LinkedUserToBasename.objects.create(
                basename=validated_data['basename'],
                linked_user=validated_data['linked_user']
            )
        except IntegrityError as e:
            raise serializers.ValidationError(
                {f'Ошибка сохранения: {str(e)}'}
            )
        return linked


class UnlinkUserToBasenameSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def validate(self, attrs):
        """Проверка наличия связи."""
        linked_user_id = attrs['id']
        basename_id = self.context.get('basename_id')
        try:
            linked_user = User.objects.get(pk=linked_user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f'Пользователь с id {linked_user_id} не найден.'
            )
        try:
            basename = Basename.objects.get(pk=basename_id)
        except Basename.DoesNotExist:
            raise serializers.ValidationError(
                f'База с id {basename_id} не найдена.'
            )
        try:
            linked_object = LinkedUserToBasename.objects.get(
                basename=basename,
                linked_user=linked_user
            )
        except LinkedUserToBasename.DoesNotExist:
            raise serializers.ValidationError(
                f'Связь между пользователем id {linked_user_id} и базой '
                f'id {basename_id} не найдена.'
            )
        attrs['linked_user'] = linked_user
        attrs['basename'] = basename
        attrs['linked_object'] = linked_object
        return attrs

    def delete(self, validated_data):
        """Отключение пользователя от базы."""
        try:
            validated_data['linked_object'].delete()
        except IntegrityError as e:
            raise serializers.ValidationError(
                {f'Ошибка сохранения: {str(e)}'}
            )
