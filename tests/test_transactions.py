from decimal import Decimal

import pytest

from users.models import User

pytestmark = pytest.mark.django_db(transaction=True)


class TestTransaction:
    url = '/api/v1/transactions/'

    def test_create_transaction_and_change_summary(
            self,
            client,
            user_2_tg_only,
            user_2_auth_header,
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
            headers=user_2_auth_header,
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
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('100.00')
        data['value_transaction'] = '-50.5'
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        summary_1.refresh_from_db()
        assert summary_1.fact_value == Decimal('49.50')

    def test_list_transactions(
            self,
            client,
            user_2_auth_header,
            transaction_1,
            transaction_2
    ):
        response = client.get(
            self.url.format(user_id=transaction_1.author.id),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 2

    def test_get_transaction(self, client, user_2_auth_header, transaction_1):
        response = client.get(
            f'{self.url.format(user_id=transaction_1.author.id)}'
            f'{transaction_1.id}/',
            headers=user_2_auth_header,
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
        assert 'created_at' in response.data
        assert 'updated_at' in response.data


class TestSummary:
    url = '/api/v1/summary/'
    url_detail = '/api/v1/summary/{id}/'

    def test_list_summary(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            summary_1,
            summary_2
    ):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'sum_income_plan' in response.data
        assert 'sum_income_fact' in response.data
        assert 'sum_expense_plan' in response.data
        assert 'sum_expense_fact' in response.data
        assert 'balance_plan' in response.data
        assert 'balance_fact' in response.data
        assert 'id' in response.data['summary'][0]
        assert 'space' in response.data['summary'][0]
        assert 'period_month' in response.data['summary'][0]
        assert 'period_year' in response.data['summary'][0]
        assert 'type_transaction' in response.data['summary'][0]
        assert 'group_name' in response.data['summary'][0]
        assert 'plan_value' in response.data['summary'][0]
        assert 'fact_value' in response.data['summary'][0]
        assert 'created_at' in response.data['summary'][0]
        assert 'updated_at' in response.data['summary'][0]

    def test_get_group(self, client, user_2_auth_header, user_2_tg_only, summary_1):
        response = client.get(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=summary_1.id
            ),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert summary_1.id == response.data['id']
        assert summary_1.space.id == response.data['space']['id']
        assert summary_1.period_month == response.data['period_month']
        assert summary_1.period_year == response.data['period_year']
        assert summary_1.type_transaction == response.data['type_transaction']
        assert summary_1.group_name == response.data['group_name']
        assert (Decimal(str(summary_1.plan_value)) ==
                Decimal(response.data['plan_value']))
        assert (Decimal(str(summary_1.fact_value)) ==
                Decimal(response.data['fact_value']))
        assert 'created_at' in response.data
        assert 'updated_at' in response.data

    def test_create_group(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only
    ):
        data = {
            'group_name': 'Test_income',
            'type_transaction': 'income',
            'plan_value': '100.00',
            'fact_value': '0.00'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert 'id' in response.data
        assert response.data['group_name'] == data['group_name']
        assert response.data['type_transaction'] == data['type_transaction']
        assert response.data['plan_value'] == data['plan_value']
        assert response.data['fact_value'] == data['fact_value']
        response = client.get(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=response.data['id']
            ),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'id' in response.data
        assert 'space' in response.data
        assert (response.data['period_month'] ==
                user_2_tg_only.core_settings.current_month)
        assert (response.data['period_year'] ==
                user_2_tg_only.core_settings.current_year)
        assert response.data['group_name'] == data['group_name']
        assert response.data['type_transaction'] == data['type_transaction']
        assert response.data['plan_value'] == data['plan_value']
        assert response.data['fact_value'] == data['fact_value']
        assert 'created_at' in response.data
        assert 'updated_at' in response.data

    def test_create_double(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            summary_1
    ):
        data = {
            'group_name': summary_1.group_name,
            'type_transaction': summary_1.type_transaction,
            'plan_value': summary_1.plan_value,
            'fact_value': summary_1.fact_value,
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_put_group(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            summary_1
    ):
        data = {
            'group_name': 'Test_income_updated',
            'type_transaction': 'income',
            'plan_value': '150.00',
            'fact_value': '50.00'
        }
        response = client.put(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=summary_1.id
            ),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'id' in response.data
        assert response.data['group_name'] == data['group_name']
        assert response.data['type_transaction'] == data['type_transaction']
        assert (Decimal(response.data['plan_value']) ==
                Decimal(data['plan_value']))

    def test_patch_group(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            summary_1
    ):
        data = {
            'plan_value': '200.00'
        }
        response = client.patch(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=summary_1.id
            ),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'id' in response.data
        assert response.data['group_name'] == summary_1.group_name
        assert response.data['type_transaction'] == summary_1.type_transaction
        assert (Decimal(response.data['plan_value']) ==
                Decimal(data['plan_value']))
        assert (Decimal(response.data['fact_value']) ==
                Decimal(summary_1.fact_value))

    def test_delete_group(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            summary_1
    ):
        response = client.delete(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=summary_1.id
            ),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            self.url_detail.format(
                user_id=user_2_tg_only.id,
                id=summary_1.id
            ),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 404


class TestSpace:

    url = '/api/v1/spaces/'

    def test_create_space(self, client, user_2_auth_header, user_2_tg_only):
        data = {
            'name': 'Test_space'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert 'id' in response.data
        assert response.data['name'] == data['name'].lower()

    def test_create_space_invalid_data(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only
    ):
        data = {
            'name': 'Test_space_7777777777777777777'
        }
        response = client.post(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_get_spaces(self, client, user_2_auth_header, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert len(response.data) == 3
        assert len(response.data['spaces']) == 1
        assert 'id' in response.data['spaces'][0]
        assert response.data['owner_id'] == user_2_tg_only.id
        assert response.data['owner_username'] == user_2_tg_only.username
        assert 'available_linked_users' in response.data['spaces'][0]
        assert 'linked_chat' in response.data['spaces'][0]

    def test_get_space(self, client, user_2_auth_header, user_2_tg_only):
        response = client.get(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_space.id}/',
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (response.data['id'] ==
                user_2_tg_only.core_settings.current_space.id)
        assert (response.data['name'] ==
                user_2_tg_only.core_settings.current_space.name)
        assert response.data['owner_username'] == user_2_tg_only.username
        assert response.data['owner_id'] == user_2_tg_only.id
        assert 'linked_chat' in response.data
        assert 'available_linked_users' in response.data

    def test_put_space(self, client, user_2_auth_header, user_2_tg_only):
        data = {
            'name': 'New_Test_name',
            'linked_chat': '-12312314'
        }
        response = client.put(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_space.id}/',
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['name'] == data['name'].lower()
        assert (response.data['linked_chat'] ==
                data['linked_chat'])

    @pytest.mark.parametrize(
        'data',
        (
            {'name': 'New_Test_space'},
            {'linked_chat': '-1243124312'}
        )
    )
    def test_patch_space(self, client, user_2_auth_header, user_2_tg_only, data):
        response = client.patch(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_space.id}/',
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        key = list(data.keys())[0]
        assert response.data[key] == data[key].lower()

    def test_delete_space(self, client, user_2_auth_header, user_2_tg_only):
        response = client.delete(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_space.id}/',
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            f'{self.url.format(user_id=user_2_tg_only.id)}'
            f'{user_2_tg_only.core_settings.current_space.id}/',
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 404


class TestLinkUsersToSpace:

    link_url = '/api/v1/spaces/{space_id}/link_user/'
    unlink_url = '/api/v1/spaces/{space_id}/unlink_user/'

    def test_link_and_unlink(
            self,
            client,
            user_1_auth_header,
            user_1,
            user_2_tg_only
    ):
        data = {'id': user_2_tg_only.id}
        response = client.post(
            self.link_url.format(space_id=user_1.core_settings.current_space.id),
            headers=user_1_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'status' in response.data
        response = client.post(
            self.unlink_url.format(
                space_id=user_1.core_settings.current_space.id
            ),
            headers=user_1_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'status' in response.data
        u = User.objects.get(pk=user_2_tg_only.id)
        assert u.core_settings.current_space is None


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
    def test_link_to_space_invalid_data(
            self,
            client,
            user_2_auth_header,
            user_1,
            user_2_tg_only,
            data,
            expected_status
    ):
        response = client.post(
            self.link_url.format(
                user_id=user_1.id,
                space_id=user_1.core_settings.current_space.id
            ),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == expected_status
        response = client.post(
            self.unlink_url.format(
                user_id=user_1.id,
                space_id=user_1.core_settings.current_space.id
            ),
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == expected_status
