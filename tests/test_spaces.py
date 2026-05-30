import pytest

from django.urls import reverse

from transactions.models import LinkedUserToSpace, Space, Summary, Transaction
from users.models import User
from transactions.permissions import (
    get_space_role,
    can_edit_space,
    is_space_owner,
    SPACE_ROLE_OWNER,
    SPACE_ROLE_EDITOR,
    SPACE_ROLE_VIEWER,
)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def space_summary(user_1, owner_space):
    """Статья в пространстве owner для тестовых POST."""
    cs = user_1.core_settings
    return Summary.objects.create(
        space=owner_space,
        period_month=cs.current_month,
        period_year=cs.current_year,
        type_transaction='income',
        group_name='enf_group',
        plan_value=100,
    )


class TestRoleModel:

    def test_linked_role_default_viewer(self, owner_space, make_user):
        """Новая связь без явной роли получает viewer."""
        link = LinkedUserToSpace.objects.create(
            space=owner_space,
            linked_user=make_user('role_default'),
        )
        assert link.role == SPACE_ROLE_VIEWER


class TestGetSpaceRole:

    def test_owner(self, user_1, owner_space):
        """Владелец пространства → owner."""
        assert get_space_role(user_1, owner_space) == SPACE_ROLE_OWNER

    @pytest.mark.parametrize('role', [SPACE_ROLE_EDITOR, SPACE_ROLE_VIEWER])
    def test_member_role(self, owner_space, make_user, role):
        """Участник со связью получает свою роль."""
        member = make_user(f'role_{role}')
        LinkedUserToSpace.objects.create(
            space=owner_space, linked_user=member, role=role,
        )
        assert get_space_role(member, owner_space) == role

    def test_none_for_non_member(self, owner_space, make_user):
        """Юзер без связи и не владелец → None."""
        assert get_space_role(make_user('role_stranger'), owner_space) is None

    def test_none_for_no_space(self, user_1):
        """space=None → None."""
        assert get_space_role(user_1, None) is None


class TestEnforcement:
    """Шаг 2 — блокировка мутаций по роли в current_space."""

    # ------------------------------------------------------------------ viewer заблокирован

    def test_viewer_cannot_add_transaction(self, viewer_client, space_summary):
        """viewer POST add_transaction → редирект, Transaction не создана."""
        count_before = Transaction.objects.count()
        resp = viewer_client.post(reverse('transactions:add_transaction'), {
            'type_transaction': 'income',
            'group_name': space_summary.group_name,
            'value_transaction': '10',
        })
        assert resp.status_code == 302
        assert Transaction.objects.count() == count_before

    def test_viewer_cannot_add_summary(self, viewer_client):
        """viewer POST add_summary → редирект, Summary не создана."""
        count_before = Summary.objects.count()
        resp = viewer_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'income',
            'group_name': 'blocked_group',
            'plan_value': '100',
        })
        assert resp.status_code == 302
        assert Summary.objects.count() == count_before

    def test_viewer_cannot_create_period(self, viewer, viewer_client):
        """viewer POST create_period → редирект, Summary не создана, период не меняется."""
        count_before = Summary.objects.count()
        original_month = viewer.core_settings.current_month
        original_year = viewer.core_settings.current_year
        resp = viewer_client.post(reverse('transactions:create_period'), {
            'period_month': '3',
            'period_year': '2030',
            'next': '/',
        })
        assert resp.status_code == 302
        assert Summary.objects.count() == count_before
        viewer.core_settings.refresh_from_db()
        assert viewer.core_settings.current_month == original_month
        assert viewer.core_settings.current_year == original_year

    def test_viewer_cannot_delete_summary(self, viewer_client, space_summary):
        """viewer POST delete_summary → редирект, Summary остаётся."""
        resp = viewer_client.post(
            reverse('transactions:delete_summary', args=[space_summary.pk])
        )
        assert resp.status_code == 302
        assert Summary.objects.filter(pk=space_summary.pk).exists()

    # ------------------------------------------------------------------ editor разрешено

    def test_editor_can_add_summary(self, editor_client):
        """editor POST add_summary → Summary создана."""
        count_before = Summary.objects.count()
        editor_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'income',
            'group_name': 'editor_group',
            'plan_value': '50',
        })
        assert Summary.objects.count() == count_before + 1

    def test_editor_can_delete_summary(self, editor_client, space_summary):
        """editor POST delete_summary → Summary удалена."""
        editor_client.post(
            reverse('transactions:delete_summary', args=[space_summary.pk])
        )
        assert not Summary.objects.filter(pk=space_summary.pk).exists()

    # ------------------------------------------------------------------ owner разрешено

    def test_owner_can_add_summary(self, user_1_client):
        """owner POST add_summary → Summary создана."""
        count_before = Summary.objects.count()
        user_1_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'income',
            'group_name': 'owner_group',
            'plan_value': '200',
        })
        assert Summary.objects.count() == count_before + 1

    def test_owner_can_delete_summary(self, user_1_client, space_summary):
        """owner POST delete_summary → Summary удалена."""
        user_1_client.post(
            reverse('transactions:delete_summary', args=[space_summary.pk])
        )
        assert not Summary.objects.filter(pk=space_summary.pk).exists()

    # ------------------------------------------------------------------ current_space=None заблокирован

    def test_no_space_cannot_add_summary(self, no_space_client):
        """current_space=None → POST add_summary заблокирован."""
        count_before = Summary.objects.count()
        resp = no_space_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'income',
            'group_name': 'nospace_group',
            'plan_value': '100',
        })
        assert resp.status_code == 302
        assert Summary.objects.count() == count_before

    def test_no_space_cannot_create_period(self, no_space_user, no_space_client):
        """current_space=None → POST create_period заблокирован, period не меняется."""
        original_month = no_space_user.core_settings.current_month
        original_year = no_space_user.core_settings.current_year
        no_space_client.post(reverse('transactions:create_period'), {
            'period_month': '6',
            'period_year': '2030',
            'next': '/',
        })
        no_space_user.core_settings.refresh_from_db()
        assert no_space_user.core_settings.current_month == original_month
        assert no_space_user.core_settings.current_year == original_year

    # ------------------------------------------------------------------ не-участник заблокирован

    def test_non_member_cannot_add_summary(self, non_member_client):
        """Не-участник POST add_summary → заблокирован."""
        count_before = Summary.objects.count()
        resp = non_member_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'income',
            'group_name': 'nonmember_group',
            'plan_value': '100',
        })
        assert resp.status_code == 302
        assert Summary.objects.count() == count_before

    def test_non_member_cannot_delete_summary(self, non_member_client, space_summary):
        """Не-участник POST delete_summary → Summary остаётся."""
        non_member_client.post(
            reverse('transactions:delete_summary', args=[space_summary.pk])
        )
        assert Summary.objects.filter(pk=space_summary.pk).exists()

    # ------------------------------------------------------------------ apply_period: разрешить при role ≠ None

    def test_viewer_can_apply_period(self, viewer, viewer_client):
        """viewer (role ≠ None) may apply_period."""
        resp = viewer_client.get(
            reverse('transactions:apply_period') + '?period=2025_3&next=/'
        )
        assert resp.status_code == 302
        viewer.core_settings.refresh_from_db()
        assert viewer.core_settings.current_month == 3
        assert viewer.core_settings.current_year == 2025

    def test_no_space_cannot_apply_period(self, no_space_user, no_space_client):
        """current_space=None (role=None) → apply_period заблокирован, period не меняется."""
        original_month = no_space_user.core_settings.current_month
        original_year = no_space_user.core_settings.current_year
        no_space_client.get(
            reverse('transactions:apply_period') + '?period=2030_9&next=/'
        )
        no_space_user.core_settings.refresh_from_db()
        assert no_space_user.core_settings.current_month == original_month
        assert no_space_user.core_settings.current_year == original_year


class TestSpaceManagement:
    """Шаг 3a — создание, переименование, удаление пространств."""

    # ------------------------------------------------------------------ create_space

    def test_create_space_success(self, user_1_client, user_1):
        """Пользователь создаёт новое пространство — Space появляется в БД."""
        count_before = Space.objects.filter(user=user_1).count()
        user_1_client.post(reverse('transactions:create_space'), {
            'name': 'newspace', 'next': '/',
        })
        assert Space.objects.filter(user=user_1).count() == count_before + 1
        assert Space.objects.filter(user=user_1, name='newspace').exists()

    def test_create_space_lowercase(self, user_1_client, user_1):
        """Имя пространства сохраняется в нижнем регистре."""
        user_1_client.post(reverse('transactions:create_space'), {
            'name': 'MySpace', 'next': '/',
        })
        assert Space.objects.filter(user=user_1, name='myspace').exists()

    def test_create_space_does_not_switch_current(self, user_1_client, user_1):
        """create_space НЕ меняет текущее пространство пользователя."""
        original = user_1.core_settings.current_space
        user_1_client.post(reverse('transactions:create_space'), {
            'name': 'anotherspace', 'next': '/',
        })
        user_1.core_settings.refresh_from_db()
        assert user_1.core_settings.current_space == original

    def test_create_space_duplicate_blocked(self, user_1_client, user_1, owner_space):
        """Дублирующееся имя → ошибка, Space не создаётся."""
        count_before = Space.objects.filter(user=user_1).count()
        user_1_client.post(reverse('transactions:create_space'), {
            'name': owner_space.name, 'next': '/',
        })
        assert Space.objects.filter(user=user_1).count() == count_before

    def test_create_space_empty_name_blocked(self, user_1_client, user_1):
        """Пустое имя → ошибка, Space не создаётся."""
        count_before = Space.objects.filter(user=user_1).count()
        user_1_client.post(reverse('transactions:create_space'), {
            'name': '', 'next': '/',
        })
        assert Space.objects.filter(user=user_1).count() == count_before

    def test_create_space_name_too_long_blocked(self, user_1_client, user_1):
        """Имя длиннее 20 символов → ошибка, Space не создаётся."""
        count_before = Space.objects.filter(user=user_1).count()
        user_1_client.post(reverse('transactions:create_space'), {
            'name': 'a' * 21, 'next': '/',
        })
        assert Space.objects.filter(user=user_1).count() == count_before

    # ------------------------------------------------------------------ rename_space

    def test_rename_space_success(self, user_1_client, owner_space):
        """Владелец успешно переименовывает пространство."""
        user_1_client.post(
            reverse('transactions:rename_space', args=[owner_space.pk]),
            {'name': 'renamed', 'next': '/'},
        )
        owner_space.refresh_from_db()
        assert owner_space.name == 'renamed'

    def test_rename_space_lowercase(self, user_1_client, owner_space):
        """Переименование приводит имя к нижнему регистру."""
        user_1_client.post(
            reverse('transactions:rename_space', args=[owner_space.pk]),
            {'name': 'MyNewName', 'next': '/'},
        )
        owner_space.refresh_from_db()
        assert owner_space.name == 'mynewname'

    def test_rename_space_duplicate_blocked(self, user_1_client, owner_space, second_space):
        """Переименование в уже существующее имя → ошибка, имя не меняется."""
        original_name = owner_space.name
        user_1_client.post(
            reverse('transactions:rename_space', args=[owner_space.pk]),
            {'name': second_space.name, 'next': '/'},
        )
        owner_space.refresh_from_db()
        assert owner_space.name == original_name

    def test_rename_space_non_owner_blocked(self, editor_client, owner_space):
        """Не-владелец не может переименовать чужое пространство."""
        original_name = owner_space.name
        editor_client.post(
            reverse('transactions:rename_space', args=[owner_space.pk]),
            {'name': 'hacked', 'next': '/'},
        )
        owner_space.refresh_from_db()
        assert owner_space.name == original_name

    # ------------------------------------------------------------------ delete_space

    def test_delete_space_success(self, user_1_client, user_1, owner_space, second_space):
        """Владелец удаляет не-последнее пространство — оно исчезает из БД."""
        user_1.core_settings.current_space = second_space
        user_1.core_settings.save()
        user_1_client.post(
            reverse('transactions:delete_space', args=[owner_space.pk]),
            {'next': '/'},
        )
        assert not Space.objects.filter(pk=owner_space.pk).exists()

    def test_delete_last_space_blocked(self, user_1_client, owner_space):
        """Нельзя удалить последнее собственное пространство."""
        user_1_client.post(
            reverse('transactions:delete_space', args=[owner_space.pk]),
            {'next': '/'},
        )
        assert Space.objects.filter(pk=owner_space.pk).exists()

    def test_delete_active_space_switches_owner_current(
        self, user_1_client, user_1, owner_space, second_space
    ):
        """Удаление активного пространства → владелец переключается на другое своё."""
        # owner_space — активное (установлено в фикстуре user_1)
        user_1_client.post(
            reverse('transactions:delete_space', args=[owner_space.pk]),
            {'next': '/'},
        )
        user_1.core_settings.refresh_from_db()
        assert user_1.core_settings.current_space == second_space

    def test_delete_space_linked_user_gets_null_current(
        self, user_1_client, user_1, owner_space, second_space, user_3_shared_space
    ):
        """Удаление пространства → у linked-юзера current_space=None (SET_NULL)."""
        user_1.core_settings.current_space = second_space
        user_1.core_settings.save()
        user_1_client.post(
            reverse('transactions:delete_space', args=[owner_space.pk]),
            {'next': '/'},
        )
        user_3_shared_space.core_settings.refresh_from_db()
        assert user_3_shared_space.core_settings.current_space is None

    def test_delete_space_non_owner_blocked(self, editor_client, owner_space):
        """Не-владелец не может удалить чужое пространство."""
        editor_client.post(
            reverse('transactions:delete_space', args=[owner_space.pk]),
            {'next': '/'},
        )
        assert Space.objects.filter(pk=owner_space.pk).exists()


class TestApplyAndLeaveSpace:
    """Шаг 3b — переключение активного пространства и выход из него."""

    # ------------------------------------------------------------------ apply_space

    def test_apply_space_member_switches(self, no_space_user, no_space_client, owner_space):
        """Участник (linked) может переключить current_space через apply_space."""
        LinkedUserToSpace.objects.create(
            space=owner_space, linked_user=no_space_user, role=LinkedUserToSpace.VIEWER,
        )
        no_space_client.post(reverse('transactions:apply_space'), {
            'space': owner_space.pk, 'next': '/',
        })
        no_space_user.core_settings.refresh_from_db()
        assert no_space_user.core_settings.current_space == owner_space

    def test_apply_space_owner_switches(self, user_1_client, user_1, second_space):
        """Владелец может переключить current_space на своё другое пространство."""
        user_1_client.post(reverse('transactions:apply_space'), {
            'space': second_space.pk, 'next': '/',
        })
        user_1.core_settings.refresh_from_db()
        assert user_1.core_settings.current_space == second_space

    def test_apply_space_non_member_blocked(self, no_space_user, no_space_client, owner_space):
        """Не-участник не может переключить current_space на чужое пространство."""
        no_space_client.post(reverse('transactions:apply_space'), {
            'space': owner_space.pk, 'next': '/',
        })
        no_space_user.core_settings.refresh_from_db()
        assert no_space_user.core_settings.current_space is None

    # ------------------------------------------------------------------ leave_space

    def test_leave_space_removes_link(self, viewer, viewer_client, owner_space):
        """Участник покидает пространство — LinkedUserToSpace удаляется."""
        viewer_client.post(
            reverse('transactions:leave_space', args=[owner_space.pk]), {'next': '/'},
        )
        assert not LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=viewer,
        ).exists()

    def test_leave_space_clears_current_space(self, viewer, viewer_client, owner_space):
        """Участник покидает активное пространство — current_space становится None."""
        viewer_client.post(
            reverse('transactions:leave_space', args=[owner_space.pk]), {'next': '/'},
        )
        viewer.core_settings.refresh_from_db()
        assert viewer.core_settings.current_space is None

    def test_leave_space_non_active_keeps_current_space(self, viewer, viewer_client, owner_space, second_space):
        """Участник покидает НЕ активное пространство — current_space не меняется."""
        viewer.core_settings.current_space = None
        viewer.core_settings.save()
        viewer_client.post(
            reverse('transactions:leave_space', args=[owner_space.pk]), {'next': '/'},
        )
        viewer.core_settings.refresh_from_db()
        assert viewer.core_settings.current_space is None

    def test_owner_cannot_leave_own_space(self, user_1_client, user_1, owner_space):
        """Владелец не может покинуть своё пространство через leave_space."""
        user_1_client.post(
            reverse('transactions:leave_space', args=[owner_space.pk]), {'next': '/'},
        )
        assert Space.objects.filter(pk=owner_space.pk, user=user_1).exists()

    def test_non_member_cannot_leave(self, non_member_client, owner_space):
        """Не-участник не может покинуть пространство, в котором не состоит."""
        count_before = LinkedUserToSpace.objects.filter(space=owner_space).count()
        non_member_client.post(
            reverse('transactions:leave_space', args=[owner_space.pk]), {'next': '/'},
        )
        assert LinkedUserToSpace.objects.filter(space=owner_space).count() == count_before


class TestRoleHelpers:

    @pytest.mark.parametrize('role, expected', [
        (SPACE_ROLE_OWNER, True),
        (SPACE_ROLE_EDITOR, True),
        (SPACE_ROLE_VIEWER, False),
        (None, False),
    ])
    def test_can_edit_space(self, role, expected):
        assert can_edit_space(role) is expected

    @pytest.mark.parametrize('role, expected', [
        (SPACE_ROLE_OWNER, True),
        (SPACE_ROLE_EDITOR, False),
        (SPACE_ROLE_VIEWER, False),
        (None, False),
    ])
    def test_is_space_owner(self, role, expected):
        assert is_space_owner(role) is expected


class TestSpaceMembers:
    """Шаг 3c — приглашение, смена роли и исключение участников (владелец)."""

    # ------------------------------------------------------------------ invite_user

    def test_invite_success_with_role(self, user_1_client, owner_space, make_user):
        """Владелец приглашает существующего юзера с ролью editor → доступ сразу."""
        target = make_user('inviteme')
        user_1_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': 'inviteme', 'role': LinkedUserToSpace.EDITOR, 'next': '/'},
        )
        link = LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=target,
        ).first()
        assert link is not None
        assert link.role == LinkedUserToSpace.EDITOR
        assert get_space_role(target, owner_space) == SPACE_ROLE_EDITOR

    def test_invite_lowercases_username(self, user_1_client, owner_space, make_user):
        """Логин приводится к нижнему регистру при поиске юзера."""
        target = make_user('inviteme')
        user_1_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': 'INVITEME', 'role': LinkedUserToSpace.VIEWER, 'next': '/'},
        )
        assert LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=target,
        ).exists()

    def test_invite_self_blocked(self, user_1_client, user_1, owner_space):
        """Владелец не может пригласить сам себя."""
        user_1_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': user_1.username, 'role': LinkedUserToSpace.VIEWER, 'next': '/'},
        )
        assert not LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=user_1,
        ).exists()

    def test_invite_duplicate_blocked(self, user_1_client, owner_space, viewer):
        """Повторное приглашение уже-участника → новой связи не появляется."""
        count_before = LinkedUserToSpace.objects.filter(space=owner_space).count()
        user_1_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': viewer.username, 'role': LinkedUserToSpace.EDITOR, 'next': '/'},
        )
        assert LinkedUserToSpace.objects.filter(space=owner_space).count() == count_before

    def test_invite_nonexistent_user_blocked(self, user_1_client, owner_space):
        """Приглашение несуществующего логина → связи нет."""
        user_1_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': 'ghost', 'role': LinkedUserToSpace.VIEWER, 'next': '/'},
        )
        assert not LinkedUserToSpace.objects.filter(space=owner_space).exists()

    def test_invite_non_owner_blocked(self, editor_client, owner_space, make_user):
        """Не-владелец не может приглашать в чужое пространство."""
        make_user('inviteme')
        editor_client.post(
            reverse('transactions:invite_user', args=[owner_space.pk]),
            {'username': 'inviteme', 'role': LinkedUserToSpace.VIEWER, 'next': '/'},
        )
        target = User.objects.get(username='inviteme')
        assert not LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=target,
        ).exists()

    # ------------------------------------------------------------------ change_member_role

    def test_change_role_success(self, user_1_client, owner_space, viewer):
        """Владелец меняет роль участника viewer → editor."""
        user_1_client.post(
            reverse('transactions:change_member_role', args=[owner_space.pk]),
            {'linked_user_id': viewer.pk, 'role': LinkedUserToSpace.EDITOR, 'next': '/'},
        )
        link = LinkedUserToSpace.objects.get(space=owner_space, linked_user=viewer)
        assert link.role == LinkedUserToSpace.EDITOR

    def test_change_role_non_owner_blocked(self, editor_client, owner_space, viewer):
        """Не-владелец не может менять роли участников."""
        editor_client.post(
            reverse('transactions:change_member_role', args=[owner_space.pk]),
            {'linked_user_id': viewer.pk, 'role': LinkedUserToSpace.EDITOR, 'next': '/'},
        )
        link = LinkedUserToSpace.objects.get(space=owner_space, linked_user=viewer)
        assert link.role == LinkedUserToSpace.VIEWER

    # ------------------------------------------------------------------ remove_member

    def test_remove_member_success(self, user_1_client, owner_space, viewer):
        """Владелец исключает участника — связь удаляется."""
        user_1_client.post(
            reverse('transactions:remove_member', args=[owner_space.pk]),
            {'linked_user_id': viewer.pk, 'next': '/'},
        )
        assert not LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=viewer,
        ).exists()

    def test_remove_member_resets_current_space(self, user_1_client, owner_space, viewer):
        """Исключённый участник, у которого это было current_space → сброс в None."""
        assert viewer.core_settings.current_space == owner_space
        user_1_client.post(
            reverse('transactions:remove_member', args=[owner_space.pk]),
            {'linked_user_id': viewer.pk, 'next': '/'},
        )
        viewer.core_settings.refresh_from_db()
        assert viewer.core_settings.current_space is None

    def test_remove_member_non_owner_blocked(self, editor_client, owner_space, viewer):
        """Не-владелец не может исключать участников."""
        editor_client.post(
            reverse('transactions:remove_member', args=[owner_space.pk]),
            {'linked_user_id': viewer.pk, 'next': '/'},
        )
        assert LinkedUserToSpace.objects.filter(
            space=owner_space, linked_user=viewer,
        ).exists()


class TestSpacesContextProcessor:
    """Шаг 4 — context-processor spaces_and_role: роль, права, список пространств."""

    def test_owner_role_keys(self, user_1_client):
        """Для владельца: role=own, can_edit=True, is_owner=True."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert resp.context['current_space_role'] == SPACE_ROLE_OWNER
        assert resp.context['current_space_can_edit'] is True
        assert resp.context['current_space_is_owner'] is True

    def test_editor_role_keys(self, editor_client):
        """Для участника-редактора: role=editor, can_edit=True, is_owner=False."""
        resp = editor_client.get(reverse('transactions:summary'))
        assert resp.context['current_space_role'] == SPACE_ROLE_EDITOR
        assert resp.context['current_space_can_edit'] is True
        assert resp.context['current_space_is_owner'] is False

    def test_no_space_keys(self, no_space_client):
        """current_space=None → role=None, can_edit=False, is_owner=False."""
        resp = no_space_client.get(reverse('transactions:summary'))
        assert resp.context['current_space_role'] is None
        assert resp.context['current_space_can_edit'] is False
        assert resp.context['current_space_is_owner'] is False

    def test_available_spaces_contains_space(self, user_1_client, owner_space):
        """available_spaces содержит пространство пользователя."""
        resp = user_1_client.get(reverse('transactions:summary'))
        assert owner_space.pk in {s.pk for s in resp.context['available_spaces']}

    def test_own_space_plain_display_name(self, user_1_client, owner_space):
        """Своё пространство отображается простым именем."""
        resp = user_1_client.get(reverse('transactions:summary'))
        spaces = {s.pk: s for s in resp.context['available_spaces']}
        assert spaces[owner_space.pk].display_name == owner_space.name

    def test_foreign_space_marked_with_owner(self, editor_client, owner_space):
        """Чужое пространство помечено владельцем: «имя · от <owner>»."""
        resp = editor_client.get(reverse('transactions:summary'))
        spaces = {s.pk: s for s in resp.context['available_spaces']}
        assert ' · от ' in spaces[owner_space.pk].display_name
