from datetime import datetime
from pprint import pprint

import pytest
from django.conf import settings

from tests.conftest import auth_header
from transactions.models import Space
from users.models import TelegramSettings, CoreSettings, User

pytestmark = pytest.mark.django_db(transaction=True)


class TestJWT:

    url = '/api/v1/auth/jwt/'
    user_test_password = '123456user'

    def test_jwt_create(self, client, user_1):
        response = client.post(
            f'{self.url}create',
            data={
                'username': user_1.username,
                'password': self.user_test_password,
            }
        )

        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_jwt_verify(self, client, user_1):
        response_create_token = client.post(
            f'{self.url}create',
            data={
                'username': user_1.username,
                'password': self.user_test_password,
            }
        )
        response_verify = client.post(
            f'{self.url}verify',
            data={
                'token': response_create_token.data['access'],
            }
        )

        assert response_verify.status_code == 200

    def test_jwt_refresh(self, client, user_1):
        response_create_token = client.post(
            f'{self.url}create',
            data={
                'username': user_1.username,
                'password': self.user_test_password,
            }
        )
        response_refresh = client.post(
            f'{self.url}refresh',
            data={
                'refresh': response_create_token.data['refresh'],
            }
        )

        assert response_refresh.status_code == 200
        assert 'access' in response_refresh.data


class TestUser:

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
    def test_create_user(self, client, admin_auth_header, data):
        response = client.post(
            self.url,
            headers=admin_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert data['username'] == response.data['username']
        assert 'id' in response.data
        assert 'email' in response.data
        assert 'first_name' in response.data
        assert 'last_name' in response.data
        assert TelegramSettings.objects.filter(user_id=response.data['id']).exists()
        assert CoreSettings.objects.filter(user_id=response.data['id']).exists()
        assert Space.objects.filter(user_id=response.data['id']).exists()

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
    def test_create_user_invalid_data(self, client, admin_auth_header, data):
        response = client.post(
            self.url,
            headers=admin_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_create_user_not_allowed_username(self, client, admin_auth_header):
        data = {
            'password': 'testpassword1234',
            'telegram_only': False
        }
        for username in settings.NOT_ALLOWED_USERNAMES:
            data['username'] = username
            response = client.post(
                self.url,
                headers=admin_auth_header,
                data=data,
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_get_all_users(self, client, admin_auth_header, user_1, user_2_tg_only):
        response = client.get(
            self.url,
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 3  # 3 юзера, т.к. еще админ

    def test_filter_username_users(
            self,
            client,
            admin_auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?username={user_1.username}',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['username'] == user_1.username

    def test_filter_telegram_only_users(
            self,
            client,
            admin_auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?telegram_only=true',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert (response.data['results'][0]['username'] ==
                user_2_tg_only.username)

    def test_filter_id_telegram_users(
            self,
            client,
            admin_auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?'
            f'id_telegram={user_2_tg_only.telegram_settings.id_telegram}',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert (response.data['results'][0]['username'] ==
                user_2_tg_only.username)

    def test_filter_email_users(
            self,
            client,
            admin_auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?email={user_1.email}',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['username'] == user_1.username

    @pytest.mark.parametrize(
        'user',
        [
            'user_1',
            'user_2_tg_only'
        ]
    )
    def test_get_user(self, request, client, admin_auth_header, user):
        user_instance = request.getfixturevalue(user)
        response = client.get(
            f'{self.url}{user_instance.id}/',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert user_instance.username == response.data['username']
        assert user_instance.id == response.data['id']
        assert user_instance.email == response.data['email']
        assert user_instance.first_name == response.data['first_name']
        assert user_instance.last_name == response.data['last_name']
        assert 'core_settings' in response.data
        assert 'telegram_settings' in response.data
        assert 'spaces' in response.data


    def test_put_user(self, client, admin_auth_header, user_1):
        data = {
            "username": "BdgGEZ1TFkNCvtK7Tpw66y",
            "password": "string252341"
        }
        response = client.put(
            f'{self.url}{user_1.id}/',
            headers=admin_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['username'].lower() == response.data['username']

    @pytest.mark.parametrize(
        'data',
        [
            {'username': 'updated_testuser'},
            {'email': 'testuser@example.com'},
            {'first_name': 'John'},
            {'last_name': 'Doe'},
        ]
    )
    def test_patch_user(self, client, admin_auth_header, user_1, data):
        response = client.patch(
            f'{self.url}{user_1.id}/',
            headers=admin_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        for key in data:
            assert data[key] == response.data[key]

    def test_delete_user(self, client, admin_auth_header, user_1):
        response = client.delete(
            f'{self.url}{user_1.id}/',
            headers=admin_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204


class TestProfile:
    url = '/api/v1/profile/'

    def test_unauthenticated(self, client):
        response = client.get(
            self.url,
            headers={'Authorization': 'Bearer 123'},
        )
        assert response.status_code == 401

    def test_get_profile(self, client, user_1, user_1_auth_header):
        response = client.get(
            self.url,
            headers=user_1_auth_header
        )
        assert response.status_code == 200
        assert response.data['id'] == user_1.id
        assert response.data['username'] == user_1.username
        assert response.data['email'] == user_1.email
        assert response.data['first_name'] == user_1.first_name
        assert response.data['last_name'] == user_1.last_name
        assert 'date_joined' in response.data
        assert 'last_login' in response.data
        assert 'core_settings' in response.data
        assert 'telegram_settings' in response.data
        assert 'spaces' in response.data
        assert 'available_linked_spaces' in response.data

    def test_patch_profile(
            self,
            client,
            user_1_auth_header,
            user_1
    ):
        data = {
            'email': 'updated_testuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        response = client.patch(
            self.url,
            headers=user_1_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['id'] == user_1.id
        assert response.data['email'] == data['email']
        assert response.data['first_name'] == data['first_name']
        assert response.data['last_name'] == data['last_name']


class TestCoreSettings:

    url = '/api/v1/profile/core-settings/'

    def test_unauthenticated(self, client):
        response = client.get(
            self.url,
            headers={'Authorization': 'Bearer 123'},
        )
        assert response.status_code == 401

    def test_get_core_settings(
            self,
            client,
            user_2_tg_only,
            user_2_auth_header
    ):
        response = client.get(
            self.url,
            headers=user_2_auth_header,
            content_type='application/json'
        )
        dt = datetime.now()
        assert response.status_code == 200
        assert (user_2_tg_only.core_settings.current_space.id ==
                response.data['current_space']['id'])
        assert response.data['current_month'] == dt.month
        assert response.data['current_year'] == dt.year


    def test_patch_core_settings(
            self,
            client,
            user_2_auth_header,
            user_1,
            user_2_tg_only
    ):
        data = {
            'current_month': 11,
            'current_space_id': user_1.core_settings.current_space.id
        }
        response = client.patch(
            self.url,
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['current_month'] == response.data['current_month']
        assert data['current_space_id'] == response.data['current_space_id']
        assert (user_2_tg_only.core_settings.current_year ==
                response.data['current_year'])


    @pytest.mark.parametrize(
        'data',
        (
            {'current_month': 13},
            {'current_year': 2000}
        )
    )
    def test_patch_core_settings_invalid_data(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            data
    ):
        response = client.patch(
            self.url,
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400


class TestTelegramSettings:

    url = '/api/v1/profile/telegram-settings/'

    def test_unauthenticated(self, client):
        response = client.get(
            self.url,
            headers={'Authorization': 'Bearer 123'},
        )
        assert response.status_code == 401

    def test_get_telegram_settings(self, client, user_2_auth_header, user_2_tg_only):
        response = client.get(
            self.url,
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (user_2_tg_only.telegram_settings.id_telegram ==
                response.data['id_telegram'])
        assert (user_2_tg_only.telegram_settings.telegram_only ==
                response.data['telegram_only'])
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

    def test_put_telegram_settings(self, client, user_2_auth_header, user_2_tg_only):
        data = {
            'id_telegram': 777,
            'telegram_only': False,
        }
        response = client.put(
            self.url,
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['id_telegram'] == data['id_telegram']
        assert response.data['telegram_only'] == data['telegram_only']
        assert user_2_tg_only.telegram_settings.user.username == response.data['user']

    @pytest.mark.parametrize(
        'data',
        (
            {
                'id_telegram': '12qwe3',
                'telegram_only': False,
            },
            {
                'id_telegram': 777,
                'telegram_only': 123,
            },
        )
    )
    def test_put_telegram_settings_invalid_data(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            data
    ):
        response = client.put(
            self.url,
            data=data,
            headers=user_2_auth_header,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_patch_telegram_settings(self, client, user_2_auth_header, user_2_tg_only):
        data = {'telegram_only': False}
        response = client.patch(
            self.url,
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['telegram_only'] == response.data['telegram_only']
        assert user_2_tg_only.telegram_settings.id_telegram == response.data['id_telegram']
        assert user_2_tg_only.telegram_settings.user.username == response.data['user']

    @pytest.mark.parametrize(
        'data',
        (
                {'telegram_only': 123},
                {'id_telegram': '123sa'}
        )
    )
    def test_patch_telegram_settings_invalid_data(
            self,
            client,
            user_2_auth_header,
            user_2_tg_only,
            data
    ):
        response = client.patch(
            self.url,
            headers=user_2_auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

