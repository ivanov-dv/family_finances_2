from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import UniqueConstraint

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
    basename = models.CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(fields=('user', 'basename'), name='unique_basename_user')
        ]
        default_related_name = 'basenames'


class Transaction(CreatedUpdatedModel):
    basename = models.ForeignKey(Basename, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    group_name = models.CharField()
    description = models.TextField()
    income = models.DecimalField(max_digits=10, decimal_places=2)
    expense = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        default_related_name = 'transactions'
        ordering = ('-updated_at', '-created_at')
        verbose_name = 'транзакция'
        verbose_name_plural = 'транзакции'


class Summary(CreatedUpdatedModel):
    basename = models.ForeignKey(Basename, on_delete=models.CASCADE)
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    type_transaction = models.CharField()
    group_name = models.CharField()
    plan_value = models.DecimalField(max_digits=10, decimal_places=2)
    fact_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        default_related_name ='summaries'
        ordering = ('-updated_at', '-created_at')
        verbose_name = 'свод'
        verbose_name_plural = 'своды'


class JointChat(CreatedUpdatedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    chat_id = models.CharField()

    class Meta:
        default_related_name = 'joint_chat'
        verbose_name = 'связанный чат'
        verbose_name_plural = 'связанные чаты'
