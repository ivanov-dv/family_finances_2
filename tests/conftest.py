import pytest

from users.models import User


@pytest.fixture
def user_1():
    return User.objects.create(
        username='user1',
        password='123456',
        telegram_only=False
    )


@pytest.fixture
def user_2_tg_only():
    return User.objects.create(
        username='user2_tg_only',
        id_telegram=1234567890,
        telegram_only=True
    )