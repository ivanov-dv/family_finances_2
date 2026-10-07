"""API бота: сравнение токена, длинный логин, итог статьи при добавлении операции (блокировка, переполнение)."""
import threading
from decimal import Decimal

import pytest
from django.db import connection, connections
from django.test import Client, override_settings

from api.v1.auth import authentication
from transactions.amounts import MAX_AMOUNT
from transactions.models import Space, Summary, Transaction
from users.models import CoreSettings

pytestmark = pytest.mark.django_db(transaction=True)

USERS = '/api/v1/users/'
TRANSACTIONS = '/api/v1/users/{user_id}/transactions/'


class TestTokenComparison:

    def test_exact_token_is_accepted(self, client, auth_header):
        assert client.get(USERS, headers=auth_header).status_code == 200

    def test_almost_equal_tokens_are_rejected(self, client, auth_header):
        token = auth_header['Authorization']
        variants = [token + 'x', token[:-1], token.swapcase() if token.swapcase() != token else token + '0', 'тест']
        for variant in variants:
            assert client.get(USERS, headers={'Authorization': variant}).status_code == 403, variant

    @pytest.mark.parametrize('configured', [None, ''])
    def test_unset_token_lets_nobody_in(self, client, configured):
        with override_settings(ACCESS_TOKEN=configured):
            assert client.get(USERS, headers={'Authorization': 'anything'}).status_code == 403
            assert client.get(USERS, headers={'Authorization': ''}).status_code == 403
            assert client.get(USERS).status_code == 403

    def test_comparison_goes_through_compare_digest(self, client, auth_header, monkeypatch):
        calls = []
        original = authentication.hmac.compare_digest

        def spy(a, b):
            calls.append((a, b))
            return original(a, b)

        monkeypatch.setattr(authentication.hmac, 'compare_digest', spy)
        assert client.get(USERS, headers=auth_header).status_code == 200
        assert calls and all(isinstance(x, bytes) for x in calls[0])


class TestLongUsername:
    """username до 150 символов, а Space.name — 20: регистрация владельца длинного ника падала в 500."""

    def create(self, client, auth_header, username):
        return client.post(
            USERS, headers=auth_header, content_type='application/json',
            data={'username': username, 'password': 'testpassword1234', 'telegram_only': False},
        )

    def test_space_name_is_truncated_to_the_field_length(self, client, auth_header):
        response = self.create(client, auth_header, 'a' * 30)
        assert response.status_code == 201
        space = Space.objects.get(user_id=response.data['id'])
        assert space.name == 'a' * 20
        assert CoreSettings.objects.get(user_id=response.data['id']).current_space == space

    def test_mixed_case_is_lowercased_like_the_username(self, client, auth_header):
        response = self.create(client, auth_header, 'LongTelegramUsername' + 'X' * 10)
        assert response.status_code == 201
        assert response.data['username'] == ('LongTelegramUsername' + 'X' * 10).lower()
        assert Space.objects.get(user_id=response.data['id']).name == 'longtelegramusername'

    def test_maximum_username_length_is_accepted_and_longer_is_a_400(self, client, auth_header):
        assert self.create(client, auth_header, 'b' * 150).status_code == 201
        assert self.create(client, auth_header, 'c' * 151).status_code == 400

    def test_short_username_is_unchanged(self, client, auth_header):
        response = self.create(client, auth_header, 'ivan')
        assert Space.objects.get(user_id=response.data['id']).name == 'ivan'


class TestCreateTransactionGuards:

    def post(self, client, auth_header, user, value, group='Test_income'):
        return client.post(
            TRANSACTIONS.format(user_id=user.id), headers=auth_header, content_type='application/json',
            data={'group_name': group, 'type_transaction': 'income', 'value_transaction': value},
        )

    def test_overflowing_fact_is_a_400_and_changes_nothing(self, client, auth_header, user_2_tg_only, summary_1):
        Summary.objects.filter(pk=summary_1.pk).update(fact_value=MAX_AMOUNT - 1)
        response = self.post(client, auth_header, user_2_tg_only, '5')
        assert response.status_code == 400
        assert 'value_transaction' in response.data
        assert Transaction.objects.count() == 0
        summary_1.refresh_from_db()
        assert summary_1.fact_value == MAX_AMOUNT - 1

    def test_missing_group_is_a_400_not_a_500(self, client, auth_header, user_2_tg_only, summary_1):
        response = self.post(client, auth_header, user_2_tg_only, '5', group='Нет такой')
        assert response.status_code == 400
        assert 'group_name' in response.data
        assert Transaction.objects.count() == 0

    def test_fact_accumulates_with_negative_and_fractional_values(self, client, auth_header, user_2_tg_only, summary_1):
        for value in ('10.50', '-3.25', '0.75'):
            assert self.post(client, auth_header, user_2_tg_only, value).status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('8.00')


@pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='блокировка строки (select_for_update) есть только в PostgreSQL',
)
class TestConcurrentApiTransactions:

    def test_parallel_requests_do_not_lose_updates(self, auth_header, user_2_tg_only, summary_1):
        """Бот и веб (или два бота) добавляют операции одновременно: fact_value не должен «терять» добавления."""
        workers = 8
        barrier = threading.Barrier(workers)
        statuses = []

        def worker():
            try:
                client = Client()
                barrier.wait()
                response = client.post(
                    TRANSACTIONS.format(user_id=user_2_tg_only.id), headers=auth_header, content_type='application/json',
                    data={'group_name': 'Test_income', 'type_transaction': 'income', 'value_transaction': '1'},
                )
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker) for _ in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert statuses == [201] * workers
        assert Transaction.objects.count() == workers
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal(workers)
