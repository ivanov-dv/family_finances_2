import pytest

from transactions.models import LinkedUserToSpace
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
def owner_space(user_1):
    return user_1.spaces.first()


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
