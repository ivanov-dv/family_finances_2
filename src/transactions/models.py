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


class Space(CreatedUpdatedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='spaces'
    )
    name = models.CharField(max_length=20)
    linked_users = models.ManyToManyField(
        User,
        through='LinkedUserToSpace'
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=('user', 'name'),
                name='unique_name_user'
            )
        ]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.lower()
        super().save(*args, **kwargs)


class LinkedUserToSpace(models.Model):
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE
    )
    linked_user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=('space', 'linked_user'),
                name='unique_space_linked_user'
            )
        ]


class Transaction(CreatedUpdatedModel):
    space = models.ForeignKey(Space, on_delete=models.CASCADE)
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
    space = models.ForeignKey(Space, on_delete=models.CASCADE)
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
        default_related_name = 'summaries'
        ordering = ('-updated_at', '-created_at')
        verbose_name = 'свод'
        verbose_name_plural = 'своды'
        constraints = (
            models.UniqueConstraint(
                fields=(
                    'space',
                    'period_month',
                    'period_year',
                    'group_name'
                ),
                name='unique_summary_group_name'
            ),
        )
