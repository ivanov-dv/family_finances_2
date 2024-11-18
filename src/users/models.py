from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id_telegram = models.BigIntegerField(unique=True, null=True)
    telegram_only = models.BooleanField()
    linked_users = models.ManyToManyField('User')
