from decimal import Decimal
from pprint import pprint

import pytest

pytestmark = pytest.mark.django_db


class TestTransaction:

    url = '/api/v1/users/{user_id}/transactions/'

    def test_create_transaction_and_change_summary(
            self,
            client,
            user_2_tg_only,
            summary_1
    ):
        data = {
            'group_name': 'Test_income',
            'description': 'description',
            'type_transaction': 'income',
            'value_transaction': '99.99'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert response.data['group_name'] == data['group_name']
        assert response.data['description'] == data['description']
        assert response.data['type_transaction'] == data['type_transaction']
        assert response.data['value_transaction'] == data['value_transaction']
        assert response.data['author'] == user_2_tg_only.id
        assert 'id' in response.data
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('99.99')
        data['value_transaction'] = '0.01'
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('100.00')
        data['value_transaction'] = '-50.5'
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('49.50')

    def test_list_transactions(self, client, transaction_1, transaction_2):
        response = client.get(
            self.url.format(user_id=transaction_1.author.id),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert len(response.data) == 2


    def test_get_transaction(self, client, transaction_1):
        response = client.get(
            f'{self.url.format(user_id=transaction_1.author.id)}'
            f'{transaction_1.id}/',
            content_type='application/json'
        )
        assert response.status_code == 200
        assert transaction_1.id == response.data['id']
        assert transaction_1.group_name == response.data['group_name']
        assert transaction_1.description == response.data['description']
        assert transaction_1.type_transaction == response.data['type_transaction']
        assert (Decimal(str(transaction_1.value_transaction)) ==
                Decimal(str(response.data['value_transaction'])))
        assert transaction_1.author.id == response.data['author']
