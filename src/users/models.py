from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    available_linked_basenames = models.ManyToManyField(
        'transactions.Basename',
        through='transactions.LinkedUserToBasename',
        related_name='available_linked_users',
    )

    class Meta(AbstractUser.Meta):
        ordering = ('-id',)


    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.lower()
        super().save(*args, **kwargs)


class CoreSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    current_basename = models.OneToOneField(
        'transactions.Basename',
        on_delete=models.CASCADE
    )
    current_month = models.IntegerField()
    current_year = models.IntegerField()

    class Meta:
        default_related_name ='core_settings'
        verbose_name = "core settings"
        verbose_name_plural = "core settings"


class TelegramSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_settings'
    )
    id_telegram = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_only = models.BooleanField(default=False)
    joint_chat = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "telegram settings"
        verbose_name_plural = "telegram settings"
