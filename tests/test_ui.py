import pytest

from django.urls import reverse

pytestmark = pytest.mark.django_db(transaction=True)


class TestGlobalMessages:
    """6a — единый блок messages в base.html (виден на любой странице)."""

    def test_message_rendered_on_summary(self, user_1_client, second_space):
        """Сообщение после действия видно на summary (нет своего блока — только base)."""
        resp = user_1_client.post(
            reverse('transactions:create_space'),
            {'name': 'msgspace', 'next': reverse('transactions:summary')},
            follow=True,
        )
        content = resp.content.decode()
        assert 'alert-msg' in content
        assert 'msgspace' in content

    def test_single_message_block_on_add_transaction(self, user_1_client):
        """На add_transaction сообщение рендерится один раз (нет дубля)."""
        resp = user_1_client.post(
            reverse('transactions:create_space'),
            {'name': 'oncespace', 'next': reverse('transactions:add_transaction')},
            follow=True,
        )
        content = resp.content.decode()
        assert content.count('alert-msg alert-success') == 1
