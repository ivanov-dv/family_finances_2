from datetime import datetime

import pytest
from django.conf import settings

from tests.conftest import auth_header
from transactions.models import Space
from users.models import TelegramSettings, CoreSettings

pytestmark = pytest.mark.django_db(transaction=True)


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
    def test_create_user(self, client, auth_header, data):
        response = client.post(
            self.url,
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201
        assert data['username'] == response.data['username']
        assert 'id' in response.data
        assert 'email' in response.data
        assert 'first_name' in response.data
        assert 'last_name' in response.data
        assert TelegramSettings.objects.filter(
            user_id=response.data['id']
        ).exists()
        assert CoreSettings.objects.filter(
            user_id=response.data['id']
        ).exists()
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
    def test_create_user_invalid_data(self, client, auth_header, data):
        response = client.post(
            self.url,
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_create_user_not_allowed_username(self, client, auth_header):
        data = {
            'password': 'testpassword1234',
            'telegram_only': False
        }
        for username in settings.NOT_ALLOWED_USERNAMES:
            data['username'] = username
            response = client.post(
                self.url,
                headers=auth_header,
                data=data,
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_get_all_users(self, client, auth_header, user_1, user_2_tg_only):
        response = client.get(
            self.url,
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 3  # 3 юзера, т.к. еще админ

    def test_filter_username_users(
            self,
            client,
            auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?username={user_1.username}',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['username'] == user_1.username

    def test_filter_telegram_only_users(
            self,
            client,
            auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?telegram_only=true',
            headers=auth_header,
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
            auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?'
            f'id_telegram={user_2_tg_only.telegram_settings.id_telegram}',
            headers=auth_header,
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
            auth_header,
            user_1,
            user_2_tg_only
    ):
        response = client.get(
            f'{self.url}?email={user_1.email}',
            headers=auth_header,
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
    def test_get_user(self, request, client, auth_header, user):
        user_instance = request.getfixturevalue(user)
        response = client.get(
            f'{self.url}{user_instance.id}/',
            headers=auth_header,
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


    def test_put_user(self, client, auth_header, user_1):
        data = {
            "username": "BdgGEZ1TFkNCvtK7Tpw66y",
            "password": "string252341"
        }
        response = client.put(
            f'{self.url}{user_1.id}/',
            headers=auth_header,
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
    def test_patch_user(self, client, auth_header, user_1, data):
        response = client.patch(
            f'{self.url}{user_1.id}/',
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        for key in data:
            assert data[key] == response.data[key]

    def test_delete_user(self, client, auth_header, user_1):
        response = client.delete(
            f'{self.url}{user_1.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204


class TestCoreSettings:

    url = '/api/v1/users/{user_id}/core-settings/'

    def test_get_core_settings(self, client, auth_header, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
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
            auth_header,
            user_1,
            user_2_tg_only
    ):
        data = {
            'current_month': 11,
            'current_space_id': user_1.core_settings.current_space.id
        }
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['current_month'] == response.data['current_month']
        assert (user_1.core_settings.current_space.id ==
            response.data['current_space_id'])
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
            auth_header,
            user_2_tg_only,
            data
    ):
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400


class TestTelegramSettings:

    url = '/api/v1/users/{user_id}/telegram-settings/'

    def test_get_telegram_settings(self, client, auth_header, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (user_2_tg_only.telegram_settings.id_telegram ==
                response.data['id_telegram'])
        assert (user_2_tg_only.telegram_settings.telegram_only ==
                response.data['telegram_only'])
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

    def test_put_telegram_settings(self, client, auth_header, user_2_tg_only):
        data = {
            'id_telegram': 777,
            'telegram_only': False,
        }
        response = client.put(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['id_telegram'] == data['id_telegram']
        assert response.data['telegram_only'] == data['telegram_only']
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

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
            auth_header,
            user_2_tg_only,
            data
    ):
        response = client.put(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_patch_telegram_settings(self, client, auth_header, user_2_tg_only):
        data = {'telegram_only': False}
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['telegram_only'] == response.data['telegram_only']
        assert (user_2_tg_only.telegram_settings.id_telegram ==
                response.data['id_telegram'])
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

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
            auth_header,
            user_2_tg_only,
            data
    ):
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            headers=auth_header,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 400

