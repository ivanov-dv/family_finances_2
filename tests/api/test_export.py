import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestApiExport:

    url_api = '/api/v1/users/{user_id}/export/excel/'

    def test_api_export_excel(self, client, auth_header, user_1):
        response = client.get(
            self.url_api.format(user_id=user_1.id),
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 200
        assert (response['Content-Type'] ==
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet')
        assert 'Content-Disposition' in response
        assert 'attachment; filename=' in response['Content-Disposition']
        assert 'xlsx' in response['Content-Disposition']
