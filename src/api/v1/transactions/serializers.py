from rest_framework import serializers

from family_finances import constants
from transactions.models import Transaction, Summary


class TransactionSerializer(serializers.ModelSerializer):
    type_transaction = serializers.ChoiceField(
        choices=constants.CHOICE_TYPE_TRANSACTION
    )
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('author', 'basename')

    def validate_period_month(self, period_month):
        if period_month not in range(1, 13):
            raise serializers.ValidationError(
                'Номер месяца должен быть в диапазоне от 1 до 12.'
            )
        return period_month

    def validate_period_year(self, period_year):
        if period_year not in range(2024, 2100):
            raise serializers.ValidationError(
                'Год должен быть в диапазоне от 2024 до 2099.'
            )
        return period_year


class SummarySerializer(serializers.Serializer):
    class Meta:
        fields = '__all__'
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
