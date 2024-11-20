from datetime import datetime

import pytest

from transactions.models import Basename
from users.models import TelegramSettings, CoreSettings

pytestmark = pytest.mark.django_db

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
    def test_create_user(self, client, data):
        response = client.post(
            self.url,
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
        assert Basename.objects.filter(user_id=response.data['id']).exists()

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


class TestCoreSettings:

    url = '/api/v1/users/{user_id}/core-settings/'

    def test_get_core_settings(self, client, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id)
        )
        dt = datetime.now()
        assert response.status_code == 200
        assert (user_2_tg_only.core_settings.current_basename.basename ==
                response.data['current_basename'])
        assert response.data['current_month'] == dt.month
        assert response.data['current_year'] == dt.year

    def test_put_core_settings(self, client, user_2_tg_only):
        data = {
            'current_month': 12,
            'current_year': 2022
        }
        response = client.put(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['current_month'] == response.data['current_month']
        assert data['current_year'] == response.data['current_year']
        assert (user_2_tg_only.core_settings.current_basename.basename ==
            response.data['current_basename'])

    def test_patch_core_settings(self, client, user_2_tg_only):
        data = {'current_month': 11}
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['current_month'] == response.data['current_month']
        assert (user_2_tg_only.core_settings.current_basename.basename ==
            response.data['current_basename'])
        assert (user_2_tg_only.core_settings.current_year ==
                response.data['current_year'])


class TestTelegramSettings:

    url = '/api/v1/users/{user_id}/telegram-settings/'

    def test_get_telegram_settings(self, client, user_2_tg_only):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id)
        )
        assert response.status_code == 200
        assert (user_2_tg_only.telegram_settings.id_telegram ==
                response.data['id_telegram'])
        assert (user_2_tg_only.telegram_settings.telegram_only ==
                response.data['telegram_only'])
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])
        assert (user_2_tg_only.telegram_settings.joint_chat ==
                response.data['joint_chat'])

    def test_put_telegram_settings(self, client, user_2_tg_only):
        data = {
            'id_telegram': 777,
            'telegram_only': False,
            'joint_chat': 'test_chat'
        }
        response = client.put(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.data['id_telegram'] == data['id_telegram']
        assert response.data['telegram_only'] == data['telegram_only']
        assert response.data['joint_chat'] == data['joint_chat']
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

    def test_patch_telegram_settings(self, client, user_2_tg_only):
        data = {'telegram_only': False}
        response = client.patch(
            self.url.format(user_id=user_2_tg_only.id),
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['telegram_only'] == response.data['telegram_only']
        assert (user_2_tg_only.telegram_settings.joint_chat ==
                response.data['joint_chat'])
        assert (user_2_tg_only.telegram_settings.id_telegram ==
                response.data['id_telegram'])
        assert (user_2_tg_only.telegram_settings.user.username ==
                response.data['user'])

