import pytest

pytestmark = pytest.mark.django_db


class TestAuthentication:

    url = '/api/v1/users/'
    data = {
        'username': 'testuser',
        'password': 'testpassword1234',
        'telegram_only': False
    }

    def test_valid_headers(self, client, auth_header):
        response = client.post(
            self.url,
            headers=auth_header,
            data=self.data,
            content_type='application/json'
        )
        assert response.status_code == 201

    def test_invalid_headers(self, client):
        response = client.post(
            self.url,
            headers={'Authorization': 'invalid_token'},
            data=self.data,
            content_type='application/json'
        )
        assert response.status_code == 403

    def test_no_headers(self, client):
        response = client.post(
            self.url,
            data=self.data,
            content_type='application/json'
        )
        assert response.status_code == 403
