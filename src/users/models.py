from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    available_linked_spaces = models.ManyToManyField(
        'transactions.Space',
        through='transactions.LinkedUserToSpace',
        related_name='available_linked_users',
    )

    class Meta(AbstractUser.Meta):
        ordering = ('-id',)

    def save(self, *args, **kwargs):
        if self.username:
            self.username = str(self.username).lower()
        super().save(*args, **kwargs)


class CoreSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    current_space = models.ForeignKey(
        'transactions.Space',
        on_delete=models.SET_NULL,
        null=True
    )
    current_month = models.IntegerField()
    current_year = models.IntegerField()

    class Meta:
        default_related_name = 'core_settings'
        verbose_name = 'core settings'
        verbose_name_plural = 'core settings'


class TelegramSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_settings'
    )
    id_telegram = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        default=None
    )
    telegram_only = models.BooleanField(default=False)

    class Meta:
        verbose_name = "telegram settings"
        verbose_name_plural = "telegram settings"
