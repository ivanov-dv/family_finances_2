import pytest

from tests.conftest import user_1


@pytest.mark.django_db
class TestUser:
    """Test Users model."""

    url = '/api/v1/users/'

    @pytest.mark.parametrize(
        'data',
        [
            {'username': 'testuser', 'password': 'testpassword',
             'telegram_only': False},
            {'username': 'testuser2', 'telegram_only': True,
             'id_telegram': 4351234},
        ]
    )
    def test_create_user(self, client, data):
        response = client.post(self.url, data=data)
        assert response.status_code == 201
        assert data['username'] == response.data['username']
        assert data['telegram_only'] == response.data['telegram_only']
        if 'id_telegram' in data:
            assert data['id_telegram'] == response.data['id_telegram']

    @pytest.mark.parametrize(
        'data',
        [
            {'username': 'testuser', 'telegram_only': False},
            {'username': 'testuser', 'password': ''},
            {'username': 'testuser', 'password': '1'},
            {}
        ]
    )
    def test_create_user_invalid_data(self, client, data):
        response = client.post(self.url, data=data)
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
        assert user_instance.telegram_only == response.data['telegram_only']
        assert user_instance.id_telegram == response.data['id_telegram']
        assert user_instance.id == response.data['id']
        assert user_instance.email == response.data['email']
        assert user_instance.first_name == response.data['first_name']
        assert user_instance.last_name == response.data['last_name']
        assert len(response.data['linked_users']) == 0


    def test_put_user(self, client, user_1):
        data = {'username': 'updated_testuser', 'telegram_only': True,
                'id_telegram': 4351234}
        response = client.put(
            f'{self.url}{user_1.id}/',
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['username'] == response.data['username']
        assert data['telegram_only'] == response.data['telegram_only']
        assert data['id_telegram'] == response.data['id_telegram']

    def test_patch_user(self, client, user_1):
        data = {'telegram_only': True, 'id_telegram': 4351234}
        response = client.patch(
            f'{self.url}{user_1.id}/',
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert data['telegram_only'] == response.data['telegram_only']
        assert data['id_telegram'] == response.data['id_telegram']


    def test_delete_user(self, client, user_1):
        response = client.delete(f'{self.url}{user_1.id}/')
        assert response.status_code == 204
