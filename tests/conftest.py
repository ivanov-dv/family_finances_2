from datetime import datetime

import pytest

from django.conf import settings
from transactions.models import Space, Summary, Transaction
from users.models import User, TelegramSettings, CoreSettings


@pytest.fixture
def auth_header():
    return {'Authorization': settings.ACCESS_TOKEN}


@pytest.fixture
def user_1():
    user = User.objects.create(
        username='user1',
        password='123456',
        email='user1@example.com'
    )
    TelegramSettings.objects.create(user=user, telegram_only=False)
    space = Space.objects.create(user=user, name=user.username)
    dt = datetime.now()
    CoreSettings.objects.create(
        user=user,
        current_space=space,
        current_month=dt.month,
        current_year=dt.year
    )
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
    space = Space.objects.create(user=user, name=user.username)
    dt = datetime.now()
    CoreSettings.objects.create(
        user=user,
        current_space=space,
        current_month=dt.month,
        current_year=dt.year
    )
    return user


@pytest.fixture
def summary_1(user_2_tg_only):
    return Summary.objects.create(
        space=user_2_tg_only.core_settings.current_space,
        period_month=user_2_tg_only.core_settings.current_month,
        period_year=user_2_tg_only.core_settings.current_year,
        type_transaction='income',
        group_name='Test_income',
        plan_value=10
    )

@pytest.fixture
def summary_2(user_2_tg_only):
    return Summary.objects.create(
        space=user_2_tg_only.core_settings.current_space,
        period_month=user_2_tg_only.core_settings.current_month,
        period_year=user_2_tg_only.core_settings.current_year,
        type_transaction='expense',
        group_name='Test_expense',
        plan_value=10
    )


@pytest.fixture
def transaction_1(user_2_tg_only, summary_1):
    return Transaction.objects.create(
        space=user_2_tg_only.core_settings.current_space,
        author=user_2_tg_only,
        period_month=user_2_tg_only.core_settings.current_month,
        period_year=user_2_tg_only.core_settings.current_year,
        type_transaction='income',
        group_name='Test_income',
        description='Тестовая операция 1',
        value_transaction=10.32
    )


@pytest.fixture
def transaction_2(user_2_tg_only, summary_2):
    return Transaction.objects.create(
        space=user_2_tg_only.core_settings.current_space,
        author=user_2_tg_only,
        period_month=user_2_tg_only.core_settings.current_month,
        period_year=user_2_tg_only.core_settings.current_year,
        type_transaction='expense',
        group_name='Test_expense',
        description='Тестовая операция 2',
        value_transaction=10.32
    )
