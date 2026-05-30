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


class TestProfileSpacesHub:
    """6c — хаб пространств в профиле: роль, активное, создать, сделать активным."""

    url = None  # см. reverse в тестах

    def test_create_space_button(self, user_1_client):
        """В профиле есть точка создания пространства (форма create_space)."""
        resp = user_1_client.get(reverse('users:profile'))
        assert reverse('transactions:create_space') in resp.content.decode()

    def test_owner_role_badge(self, user_1_client, owner_space):
        """Своё пространство помечено ролью «Владелец»."""
        resp = user_1_client.get(reverse('users:profile'))
        assert 'Владелец' in resp.content.decode()

    def test_apply_button_for_non_active(self, user_1_client, second_space):
        """У неактивного пространства есть форма «Сделать активным» (apply_space)."""
        resp = user_1_client.get(reverse('users:profile'))
        assert reverse('transactions:apply_space') in resp.content.decode()

    def test_active_space_marked(self, user_1_client, owner_space):
        """Активное пространство помечено меткой «Активное»."""
        resp = user_1_client.get(reverse('users:profile'))
        assert 'Активное' in resp.content.decode()

    def test_foreign_space_role_badge(self, editor_client):
        """Чужое пространство (для editor) помечено ролью «Редактирование»."""
        resp = editor_client.get(reverse('users:profile'))
        assert 'Редактирование' in resp.content.decode()

    def test_foreign_space_display_name(self, editor_client):
        """Чужое пространство отображается с владельцем «· от»."""
        resp = editor_client.get(reverse('users:profile'))
        assert ' · от ' in resp.content.decode()


class TestProfileSpaceManagement:
    """6d — управление своими пространствами, участники, «Покинуть»."""

    def test_owner_sees_rename(self, user_1_client, owner_space):
        """Владелец видит форму переименования своего пространства."""
        resp = user_1_client.get(reverse('users:profile'))
        assert reverse('transactions:rename_space', args=[owner_space.pk]) in resp.content.decode()

    def test_owner_sees_delete_when_multiple(self, user_1_client, owner_space, second_space):
        """Владелец видит удаление, когда пространств больше одного."""
        resp = user_1_client.get(reverse('users:profile'))
        assert reverse('transactions:delete_space', args=[owner_space.pk]) in resp.content.decode()

    def test_delete_hidden_when_single_owned(self, editor_client, user_3_shared_space):
        """Единственное своё пространство нельзя удалить — кнопки нет."""
        resp = editor_client.get(reverse('users:profile'))
        own = user_3_shared_space.spaces.first()
        assert reverse('transactions:delete_space', args=[own.pk]) not in resp.content.decode()

    def test_owner_sees_invite_form(self, user_1_client, owner_space):
        """Владелец видит форму приглашения участника."""
        resp = user_1_client.get(reverse('users:profile'))
        assert reverse('transactions:invite_user', args=[owner_space.pk]) in resp.content.decode()

    def test_member_list_and_controls(self, user_1_client, owner_space, viewer):
        """В списке участников — логин участника + смена роли и исключение."""
        content = user_1_client.get(reverse('users:profile')).content.decode()
        assert viewer.username in content
        assert reverse('transactions:change_member_role', args=[owner_space.pk]) in content
        assert reverse('transactions:remove_member', args=[owner_space.pk]) in content

    def test_foreign_space_leave_button(self, editor_client, owner_space):
        """У чужого пространства есть кнопка «Покинуть»."""
        resp = editor_client.get(reverse('users:profile'))
        assert reverse('transactions:leave_space', args=[owner_space.pk]) in resp.content.decode()

    def test_viewer_no_management(self, viewer_client, owner_space):
        """Не-владелец (viewer) не видит переименования/удаления/приглашения чужого."""
        content = viewer_client.get(reverse('users:profile')).content.decode()
        assert reverse('transactions:rename_space', args=[owner_space.pk]) not in content
        assert reverse('transactions:invite_user', args=[owner_space.pk]) not in content
        assert reverse('transactions:leave_space', args=[owner_space.pk]) in content


class TestSpaceSwitcher:
    """6e — переключатель пространств в sidebar + модалка."""

    def test_sidebar_card_is_trigger(self, user_1_client, owner_space):
        """Карточка активного пространства в sidebar открывает модалку переключения."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert 'data-open-app-modal="spaceSwitchModal"' in resp.content.decode()

    def test_switch_modal_present(self, user_1_client, owner_space):
        """Модалка переключения присутствует на странице."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert 'id="spaceSwitchModal"' in resp.content.decode()

    def test_switch_modal_has_apply_forms(self, user_1_client, owner_space, second_space):
        """В модалке есть формы переключения активного пространства (apply_space)."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert reverse('transactions:apply_space') in resp.content.decode()
