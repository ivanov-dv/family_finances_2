from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    linked_users = models.ManyToManyField(
        'User',
        through='LinkedUser',
    )


class LinkedUser(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    linked_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authors'
    )


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
        verbose_name = "Telegram Settings"
        verbose_name_plural = "Telegram Settings"
