from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .validators import PeriodYearValidator, PeriodMonthValidator
from family_finances import constants
from transactions.models import Transaction, Summary, Basename


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
