import pytest

from users.models import User, TelegramSettings


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
    user.refresh_from_db()
    return user