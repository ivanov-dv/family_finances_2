from rest_framework import serializers

from .validators import PeriodYearValidator, PeriodMonthValidator
from family_finances import constants
from transactions.models import Transaction, Summary, Basename


class TransactionSerializer(serializers.ModelSerializer):
    type_transaction = serializers.ChoiceField(
        choices=constants.CHOICE_TYPE_TRANSACTION
    )
    period_year = serializers.IntegerField(
        validators=(PeriodYearValidator(),)
    )
    period_month = serializers.IntegerField(
        validators=(PeriodMonthValidator(),)
    )

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('author', 'basename')


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
