from pprint import pprint

import pytest

from tests.conftest import user_1


@pytest.mark.django_db
class TestUser:
    """Test Users model."""

    url = '/api/v1/users/'

    @pytest.mark.parametrize(
        'data',
        [
            {
                'username': 'testuser',
                'password': 'testpassword1234',
                'telegram_only': False
            },
            {
                'username': 'testuser2',
                'id_telegram': 4351234,
                'telegram_only': True
            }
        ]
    )
    def test_create_user(self, client, data):
        response = client.post(
            self.url,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert data['username'] == response.data['username']
        assert (data['telegram_only'] ==
                response.data['telegram_settings']['telegram_only'])
        if data.get('id_telegram'):
            assert (data['id_telegram'] ==
                    response.data['telegram_settings']['id_telegram'])

    @pytest.mark.parametrize(
        'data',
        [
            {'username': 'testuser', 'password': ''},
            {'username': 'testuser', 'password': '1'},
            {
                'username': 'testuser',
                'telegram_only': True
            },
            {
                'username': 'testuser',
                'password': '',
                'telegram_only': False
            },
            {
                'username': 'testuser',
                'telegram_only': False
            },
        ]
    )
    def test_create_user_invalid_data(self, client, data):
        response = client.post(
            self.url,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        'user',
        [
            'user_1',
            'user_2_tg_only'
        ]
    )
    def test_get_user(self, request, client, user):
        user_instance = request.getfixturevalue(user)
        response = client.get(f'{self.url}{user_instance.id}/')
        assert response.status_code == 200
        assert user_instance.username == response.data['username']
        assert user_instance.id == response.data['id']
        assert user_instance.email == response.data['email']
        assert user_instance.first_name == response.data['first_name']
        assert user_instance.last_name == response.data['last_name']


    def test_put_user(self, client, user_1):
        data = {
            "username": "BdgGEZ1TFkNCvtK7Tpw66y",
            "password": "string252341"
        }
        response = client.put(
            f'{self.url}{user_1.id}/',
            data=data,
            content_type='application/json'
        )
        pprint(response.__dict__)
        assert response.status_code == 200
        assert data['username'] == response.data['username']

    @pytest.mark.parametrize(
        'data',
        [
            {'username': 'updated_testuser'},
            {'email': 'testuser@example.com'},
            {'first_name': 'John'},
            {'last_name': 'Doe'},
        ]
    )
    def test_patch_user(self, client, user_1, data):
        response = client.patch(
            f'{self.url}{user_1.id}/',
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        for key in data:
            assert data[key] == response.data[key]

    def test_delete_user(self, client, user_1):
        response = client.delete(f'{self.url}{user_1.id}/')
        assert response.status_code == 204
