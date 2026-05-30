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


class TestEntryPointVisibility:
    """6b — точки входа добавления скрыты для viewer, видны editor+owner."""

    def test_viewer_no_add_transaction_link(self, viewer_client):
        """viewer не видит ссылок «Новая операция»/«Добавить» (topbar+sidebar)."""
        resp = viewer_client.get(reverse('transactions:summary'))
        assert reverse('transactions:add_transaction') not in resp.content.decode()

    def test_owner_sees_add_transaction_link(self, user_1_client):
        """Владелец видит точку входа add_transaction."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert reverse('transactions:add_transaction') in resp.content.decode()

    def test_editor_sees_add_transaction_link(self, editor_client):
        """Редактор видит точку входа add_transaction."""
        resp = editor_client.get(reverse('transactions:summary'))
        assert reverse('transactions:add_transaction') in resp.content.decode()

    def test_viewer_no_add_summary_nav(self, viewer_client):
        """viewer не видит nav-ссылку на страницу статей (add_summary)."""
        resp = viewer_client.get(reverse('transactions:summary'))
        assert reverse('transactions:add_summary') not in resp.content.decode()

    def test_owner_sees_add_summary_nav(self, user_1_client):
        """Владелец видит nav-ссылку add_summary."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert reverse('transactions:add_summary') in resp.content.decode()

    def test_viewer_no_add_article_buttons(self, viewer_client):
        """На странице статей viewer не видит кнопок «Добавить статью»."""
        resp = viewer_client.get(reverse('transactions:add_summary'))
        assert 'Добавить статью' not in resp.content.decode()

    def test_owner_sees_add_article_buttons(self, user_1_client):
        """Владелец видит кнопки «Добавить статью»."""
        resp = user_1_client.get(reverse('transactions:add_summary'))
        assert 'Добавить статью' in resp.content.decode()
