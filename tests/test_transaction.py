from decimal import Decimal
from pprint import pprint

import pytest

pytestmark = pytest.mark.django_db


class TestTransaction:
    url = '/api/v1/users/{user_id}/transactions/'

    def test_create_transaction_and_change_summary(
            self,
            client,
            auth_header,
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
            headers=auth_header,
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
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('100.00')
        data['value_transaction'] = '-50.5'
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('49.50')

    def test_list_transactions(
            self,
            client,
            auth_header,
            transaction_1,
            transaction_2
    ):
        response = client.get(
            self.url.format(user_id=transaction_1.author.id),
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 2

    def test_get_transaction(self, client, auth_header, transaction_1):
        response = client.get(
            f'{self.url.format(user_id=transaction_1.author.id)}'
            f'{transaction_1.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert transaction_1.id == response.data['id']
        assert transaction_1.group_name == response.data['group_name']
        assert transaction_1.description == response.data['description']
        assert transaction_1.type_transaction == response.data[
            'type_transaction']
        assert (Decimal(str(transaction_1.value_transaction)) ==
                Decimal(str(response.data['value_transaction'])))
        assert transaction_1.author.id == response.data['author']


class TestSummary:
    url = '/api/v1/users/{user_id}/summary/'

    def test_get_summary(
            self,
            client,
            auth_header,
            user_2_tg_only,
            summary_1,
            summary_2
    ):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (response.data['current_basename_id'] ==
                user_2_tg_only.core_settings.current_basename.id)
        assert (response.data['period_month'] ==
                user_2_tg_only.core_settings.current_month)
        assert (response.data['period_year'] ==
                user_2_tg_only.core_settings.current_year)
        assert (response.data['username'] == summary_1.basename.user.username)
        assert (len(response.data['summary']) == 2)
        assert 'id' in response.data['summary'][0]
        assert 'type_transaction' in response.data['summary'][0]
        assert 'group_name' in response.data['summary'][0]
        assert 'plan_value' in response.data['summary'][0]
        assert 'fact_value' in response.data['summary'][0]
        assert 'created_at' in response.data['summary'][0]
        assert 'updated_at' in response.data['summary'][0]


class TestBasename:

    url = '/api/v1/users/{user_id}/basenames/'

    def test_create_basename(self, client, auth_header, user_2_tg_only):
        data = {
            'basename': 'Test_basename'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert 'id' in response.data
        assert response.data['basename'] == data['basename'].lower()

    def test_create_basename_invalid_data(
            self,
            client,
            auth_header,
            user_2_tg_only
    ):
        data = {
            'basename': 'Test_basename_7777777777777777777'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_get_basenames(self, client, auth_header, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert len(response.data) == 3
        assert len(response.data['basenames']) == 1
        assert 'id' in response.data['basenames'][0]
        assert response.data['owner_id'] == user_2_tg_only.id
        assert response.data['owner_username'] == user_2_tg_only.username

    def test_get_basename(self, client, auth_header, user_2_tg_only):
        response = client.get(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_basename.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (response.data['id'] ==
                user_2_tg_only.core_settings.current_basename.id)
        assert (response.data['basename'] ==
                user_2_tg_only.core_settings.current_basename.basename)

    def test_put_basename(self, client, auth_header, user_2_tg_only):
        data = {
            'basename': 'New_Test_basename'
        }
        response = client.put(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_basename.id}/',
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['basename'] == data['basename'].lower()

    def test_patch_basename(self, client, auth_header, user_2_tg_only):
        data = {
            'basename': 'New_Test_basename'
        }
        response = client.patch(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_basename.id}/',
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['basename'] == data['basename'].lower()

    def test_delete_basename(self, client, auth_header, user_2_tg_only):
        response = client.delete(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_basename.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_basename.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 404


class TestLinkUsersToBasename:

    link_url = '/api/v1/users/{user_id}/basenames/{basename_id}/link_user/'
    unlink_url = '/api/v1/users/{user_id}/basenames/{basename_id}/unlink_user/'

    def test_link_and_unlink(
            self,
            client,
            auth_header,
            user_1,
            user_2_tg_only
    ):
        data = {'id': user_2_tg_only.id}
        response = client.post(
            self.link_url.format(
                user_id=user_1.id,
                basename_id=user_1.core_settings.current_basename.id
            ),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'status' in response.data
        response = client.post(
            self.unlink_url.format(
                user_id=user_1.id,
                basename_id=user_1.core_settings.current_basename.id
            ),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'status' in response.data


    @pytest.mark.parametrize(
        'data, expected_status',
        (
            ({'id': 1}, 400),
            ({'id': '12345678901234567890'}, 400),
            ({'id': 12345678901234567890}, 400),
            ({'id': -12345678901234567890}, 400),
            ({'id': 'abcde'}, 400),
            ({'username': 'user2_tg_only'}, 400)
        )
    )
    def test_link_to_basename_invalid_data(
            self,
            client,
            auth_header,
            user_1,
            user_2_tg_only,
            data,
            expected_status
    ):
        response = client.post(
            self.link_url.format(
                user_id=user_1.id,
                basename_id=user_1.core_settings.current_basename.id
            ),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == expected_status
        response = client.post(
            self.unlink_url.format(
                user_id=user_1.id,
                basename_id=user_1.core_settings.current_basename.id
            ),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == expected_status
