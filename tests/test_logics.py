from decimal import Decimal
from pprint import pprint

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestSetNullSpace:

    def test_delete_space_other_user(
            self,
            client,
            auth_header,
            user_1,
            user_3_shared_space
    ):
        """
        Тестирование установки поля current_space в значение None
        при удалении space другого пользователя.
        """
        response = client.get(
            f'/api/v1/users/{user_3_shared_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert (user_3_shared_space.core_settings.current_space.id ==
                response.data['core_settings']['current_space']['id'])
        response = client.delete(
            f'/api/v1/users/{user_1.id}/spaces/{user_1.core_settings.current_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            f'/api/v1/users/{user_3_shared_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.data['core_settings']['current_space'] is None

    def test_delete_other_user(
            self,
            client,
            auth_header,
            user_1,
            user_3_shared_space
    ):
        """
        Тестирование установки поля current_space в значение None
        при удалении пользователя, предоставившего доступ к своему space.
        """
        response = client.get(
            f'/api/v1/users/{user_3_shared_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert (user_3_shared_space.core_settings.current_space.id ==
                response.data['core_settings']['current_space']['id'])
        response = client.delete(
            f'/api/v1/users/{user_1.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            f'/api/v1/users/{user_3_shared_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.data['core_settings']['current_space'] is None

    def test_delete_my_space(
            self,
            client,
            auth_header,
            user_1
    ):
        """
        Тестирование установки поля current_space в значение None
        при удалении своего space.
        """
        response = client.get(
            f'/api/v1/users/{user_1.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert (user_1.core_settings.current_space.id ==
                response.data['core_settings']['current_space']['id'])
        response = client.delete(
            f'/api/v1/users/{user_1.id}/'
            f'spaces/{user_1.core_settings.current_space.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.status_code == 204
        response = client.get(
            f'/api/v1/users/{user_1.id}/',
            headers=auth_header,
            content_type='application/json'
        )
        assert response.data['core_settings']['current_space'] is None
