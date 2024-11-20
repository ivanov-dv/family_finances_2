from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import UniqueConstraint

from family_finances import constants

User = get_user_model()


class CreatedUpdatedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено'
    )

    class Meta:
        abstract = True


class Basename(CreatedUpdatedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    basename = models.CharField(max_length=20)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=('user', 'basename'),
                name='unique_basename_user'
            )
        ]
        default_related_name = 'basenames'

    def save(self, *args, **kwargs):
        if self.basename:
            self.basename = self.basename.lower()
        super().save(*args, **kwargs)


class Transaction(CreatedUpdatedModel):
    basename = models.ForeignKey(Basename, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    group_name = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    type_transaction = models.CharField(
        max_length=10,
        choices=constants.CHOICE_TYPE_TRANSACTION
    )
    value_transaction = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        default_related_name = 'transactions'
        ordering = ('-updated_at', '-created_at')
        verbose_name = 'транзакция'
        verbose_name_plural = 'транзакции'


class Summary(CreatedUpdatedModel):
    basename = models.ForeignKey(Basename, on_delete=models.CASCADE)
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    type_transaction = models.CharField(
        max_length=10,
        choices=constants.CHOICE_TYPE_TRANSACTION
    )
    group_name = models.CharField(max_length=30)
    plan_value = models.DecimalField(max_digits=12, decimal_places=2)
    fact_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        default_related_name ='summaries'
        ordering = ('-updated_at', '-created_at')
        verbose_name = 'свод'
        verbose_name_plural = 'своды'
        constraints = (
            models.UniqueConstraint(
                fields=(
                    'basename',
                    'period_month',
                    'period_year',
                    'group_name'
                ),
                name='unique_summary_group_name'
            ),
        )
