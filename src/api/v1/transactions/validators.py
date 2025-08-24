from rest_framework.serializers import ValidationError


class PeriodMonthValidator:
    """Валидатор для проверки месяца в диапазоне от 1 до 12."""

    def __call__(self, period_month):
        if period_month not in range(1, 13):
            raise ValidationError(
                'Месяц должен быть в диапазоне от 1 до 12.'
            )


class PeriodYearValidator:
    """Валидатор для проверки года в диапазоне от 2024 до 2099."""

    def __call__(self, period_year):
        if period_year not in range(2024, 2100):
            raise ValidationError(
                'Год должен быть в диапазоне от 2024 до 2099.'
            )
