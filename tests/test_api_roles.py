import pytest

from transactions.models import Summary

pytestmark = pytest.mark.django_db(transaction=True)


def _summary_in(space, cs, group='api_grp', tt='income'):
    return Summary.objects.create(
        space=space,
        period_month=cs.current_month,
        period_year=cs.current_year,
        type_transaction=tt,
        group_name=group,
        plan_value=100,
    )


class TestApiTransactionRole:
    """API: создание транзакции под ролями (user_id из URL)."""

    url = '/api/v1/users/{user_id}/transactions/'

    def test_viewer_cannot_create(self, client, auth_header, viewer, owner_space):
        """viewer (user_id) не может создать транзакцию → 403."""
        _summary_in(owner_space, viewer.core_settings)
        resp = client.post(
            self.url.format(user_id=viewer.id),
            headers=auth_header,
            data={'group_name': 'api_grp', 'type_transaction': 'income', 'value_transaction': '10'},
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_editor_can_create(self, client, auth_header, user_3_shared_space, owner_space):
        """editor (user_id) может создать транзакцию → 201."""
        _summary_in(owner_space, user_3_shared_space.core_settings)
        resp = client.post(
            self.url.format(user_id=user_3_shared_space.id),
            headers=auth_header,
            data={'group_name': 'api_grp', 'type_transaction': 'income', 'value_transaction': '10'},
            content_type='application/json',
        )
        assert resp.status_code == 201

    def test_owner_can_create(self, client, auth_header, user_1, owner_space):
        """owner (user_id) может создать транзакцию → 201."""
        _summary_in(owner_space, user_1.core_settings)
        resp = client.post(
            self.url.format(user_id=user_1.id),
            headers=auth_header,
            data={'group_name': 'api_grp', 'type_transaction': 'income', 'value_transaction': '10'},
            content_type='application/json',
        )
        assert resp.status_code == 201


class TestApiSummaryRole:
    """API: CRUD статей под ролями (user_id из URL)."""

    url = '/api/v1/users/{user_id}/summary/'
    detail = '/api/v1/users/{user_id}/summary/{id}/'

    def test_viewer_cannot_create(self, client, auth_header, viewer):
        """viewer не может создать статью → 403."""
        resp = client.post(
            self.url.format(user_id=viewer.id),
            headers=auth_header,
            data={'group_name': 'g', 'type_transaction': 'income', 'plan_value': '100', 'fact_value': '0'},
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_viewer_cannot_patch(self, client, auth_header, viewer, owner_space):
        """viewer не может изменить статью → 403."""
        s = _summary_in(owner_space, viewer.core_settings)
        resp = client.patch(
            self.detail.format(user_id=viewer.id, id=s.id),
            headers=auth_header,
            data={'plan_value': '200'},
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_viewer_cannot_delete(self, client, auth_header, viewer, owner_space):
        """viewer не может удалить статью → 403."""
        s = _summary_in(owner_space, viewer.core_settings)
        resp = client.delete(
            self.detail.format(user_id=viewer.id, id=s.id),
            headers=auth_header,
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_editor_can_create(self, client, auth_header, user_3_shared_space):
        """editor может создать статью → 201."""
        resp = client.post(
            self.url.format(user_id=user_3_shared_space.id),
            headers=auth_header,
            data={'group_name': 'g_ed', 'type_transaction': 'income', 'plan_value': '100', 'fact_value': '0'},
            content_type='application/json',
        )
        assert resp.status_code == 201


class TestApiSpaceOwner:
    """API: мутации Space и участников — только владелец (user_id из URL)."""

    detail = '/api/v1/users/{user_id}/spaces/{id}/'
    link = '/api/v1/users/{user_id}/spaces/{space_id}/link_user/'

    def test_non_owner_cannot_update_space(self, client, auth_header, viewer, owner_space):
        """Не-владелец не может изменить чужое пространство (нет в queryset) → 404."""
        resp = client.patch(
            self.detail.format(user_id=viewer.id, id=owner_space.id),
            headers=auth_header,
            data={'name': 'hacked'},
            content_type='application/json',
        )
        assert resp.status_code == 404
        owner_space.refresh_from_db()
        assert owner_space.name != 'hacked'

    def test_non_owner_cannot_link_user(self, client, auth_header, viewer, owner_space, make_user):
        """Не-владелец не может привязать участника к чужому пространству → 404."""
        target = make_user('linkme')
        resp = client.post(
            self.link.format(user_id=viewer.id, space_id=owner_space.id),
            headers=auth_header,
            data={'id': target.id},
            content_type='application/json',
        )
        assert resp.status_code == 404
