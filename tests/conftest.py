from datetime import datetime

import pytest

from transactions.models import Basename
from users.models import User, TelegramSettings, CoreSettings


@pytest.fixture
def user_1():
    user = User.objects.create(
        username='user1',
        password='123456'
    )
    TelegramSettings.objects.create(user=user, telegram_only=False)
    user.refresh_from_db()
    return user


@pytest.fixture
def user_2_tg_only():
    user = User.objects.create(
        username='user2_tg_only'
    )
    TelegramSettings.objects.create(
        user=user,
        id_telegram=1234567890,
        telegram_only=True
    )
    basename = Basename.objects.create(user=user, basename=user.username)
    dt = datetime.now()
    CoreSettings.objects.create(
        user=user,
        current_basename=basename,
        current_month=dt.month,
        current_year=dt.year
    )
    return user