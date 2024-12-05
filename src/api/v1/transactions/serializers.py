from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from family_finances import constants
from transactions.models import (
    Transaction,
    Summary,
    LinkedUserToSpace,
    Space
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
        read_only_fields = ('author',)

    def create(self, validated_data):
        summary = Summary.objects.filter(
            space=validated_data['space'],
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
    space = serializers.SlugRelatedField(
        queryset=Space.objects.all(),
        slug_field='name'
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
            'space',
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
                    'space',
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
            'space',
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
        representation['owner_space_username'] = instance.space.user.username
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


class SpaceSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name')
        model = Space


class LinkUserToSpaceSerializer(serializers.Serializer):
    id = serializers.IntegerField(label='ID пользователя')

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
        space_id = self.context.get('space_id')
        space = Space.objects.filter(pk=space_id).first()
        if not space:
            raise serializers.ValidationError(
                f'У пользователя id {owner_user_id} '
                f'нет базы с id {space_id}'
            )
        if space.user.id != owner_user_id:
            raise serializers.ValidationError(
                f'У пользователя id {owner_user_id} нет базы '
                f'с id {space.id}.'
            )
        attrs['space'] = space
        attrs['linked_user'] = linked_user
        return attrs

    def create(self, validated_data):
        """Подключение пользователя к базе."""
        try:
            linked = LinkedUserToSpace.objects.create(
                space=validated_data['space'],
                linked_user=validated_data['linked_user']
            )
        except IntegrityError as e:
            raise serializers.ValidationError(
                {f'Ошибка сохранения: {str(e)}'}
            )
        return linked


class UnlinkUserToSpaceSerializer(serializers.Serializer):
    id = serializers.IntegerField(label='ID пользователя')

    def validate(self, attrs):
        """Проверка наличия связи."""
        linked_user_id = attrs['id']
        space_id = self.context.get('space_id')
        try:
            linked_user = User.objects.get(pk=linked_user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f'Пользователь с id {linked_user_id} не найден.'
            )
        try:
            space = Space.objects.get(pk=space_id)
        except Space.DoesNotExist:
            raise serializers.ValidationError(
                f'База с id {space_id} не найдена.'
            )
        try:
            linked_object = LinkedUserToSpace.objects.get(
                space=space,
                linked_user=linked_user
            )
        except LinkedUserToSpace.DoesNotExist:
            raise serializers.ValidationError(
                f'Связь между пользователем id {linked_user_id} и базой '
                f'id {space_id} не найдена.'
            )
        attrs['linked_user'] = linked_user
        attrs['space'] = space
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
