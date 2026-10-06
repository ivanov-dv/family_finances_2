import pytest
from django.urls import reverse

from transactions.models import Space
from users.models import CoreSettings, User

pytestmark = pytest.mark.django_db(transaction=True)

PASSWORD = 'Zx9!kLm2#qwe'


class TestAnonymousAccess:
    """Страницы с CurrentSpaceEditMixin отправляют аноима на вход, а не на самих себя."""

    @pytest.mark.parametrize('name', ['add_transaction', 'add_summary'])
    def test_get_redirects_to_login(self, client, name):
        url = reverse(f'transactions:{name}')
        resp = client.get(url)
        assert resp.status_code == 302
        assert resp.url == f'{reverse("login")}?next={url}'

    @pytest.mark.parametrize('name', ['add_transaction', 'add_summary'])
    def test_post_redirects_to_login(self, client, name):
        url = reverse(f'transactions:{name}')
        resp = client.post(url, {'type_transaction': 'expense'})
        assert resp.status_code == 302
        assert resp.url == f'{reverse("login")}?next={url}'


class TestLoginPage:

    def test_anonymous_sees_page_with_login_modal(self, client):
        resp = client.get(reverse('login'))
        assert resp.status_code == 200
        assert 'loginModal' in resp.content.decode()

    def test_authenticated_redirected_away(self, user_1_client):
        resp = user_1_client.get(reverse('login'))
        assert resp.status_code == 302
        assert resp.url == reverse('transactions:home')

    def test_authenticated_follows_safe_next(self, user_1_client):
        resp = user_1_client.get(f'{reverse("login")}?next=/summary/')
        assert resp.status_code == 302
        assert resp.url == '/summary/'

    def test_next_to_login_page_itself_is_not_a_loop(self, user_1_client):
        resp = user_1_client.get(f'{reverse("login")}?next={reverse("login")}')
        assert resp.status_code == 302
        assert resp.url == reverse('transactions:home')


class TestRegistration:

    url = '/users/registration/'

    def register(self, client, username, password=PASSWORD):
        return client.post(self.url, {'username': username, 'password': password}).json()

    def test_long_username_gets_truncated_space_name(self, client):
        """Space.name — 20 символов; логин длиннее не должен давать 500."""
        username = 'a' * 40
        assert self.register(client, username)['status'] == 'success'
        space = Space.objects.get(user__username=username)
        assert space.name == 'a' * 20

    def test_username_is_normalised_to_lower_case(self, client):
        assert self.register(client, 'MixedCase')['status'] == 'success'
        assert User.objects.filter(username='mixedcase').exists()

    def test_case_variant_of_existing_login_is_rejected(self, client, user_1):
        data = self.register(client, user_1.username.upper())
        assert data['status'] == 'error'
        assert any('занят' in message for message in data['message'])
        assert User.objects.filter(username__iexact=user_1.username).count() == 1

    @pytest.mark.parametrize('username', ['Guest', 'ADMIN', 'Superuser', 'me'])
    def test_reserved_names_are_case_insensitive(self, client, username):
        data = self.register(client, username)
        assert data['status'] == 'error'
        assert any('зарезервирован' in message for message in data['message'])
        assert not User.objects.filter(username=username.lower()).exists()

    def test_login_cannot_start_with_digit(self, client):
        data = self.register(client, '1ivan')
        assert data['status'] == 'error'
        assert any('цифры' in message for message in data['message'])

    @pytest.mark.parametrize('password', ['1', 'password', '12345678', 'short'])
    def test_weak_password_is_rejected(self, client, password):
        data = self.register(client, 'weakling', password)
        assert data['status'] == 'error'
        assert not User.objects.filter(username='weakling').exists()

    def test_errors_are_a_flat_list_of_strings(self, client):
        data = self.register(client, 'weakling', '1')
        assert isinstance(data['message'], list)
        assert all(isinstance(message, str) for message in data['message'])

    def test_password_spaces_are_kept(self, client):
        """Пароль не обрезается: при входе его тоже не обрезают."""
        password = f' {PASSWORD} '
        assert self.register(client, 'spacey', password)['status'] == 'success'
        user = User.objects.get(username='spacey')
        assert user.check_password(password)
        assert not user.check_password(PASSWORD)


class TestAjaxLogin:

    url = '/users/ajax-login/'

    @pytest.fixture
    def ivan(self):
        return User.objects.create_user('ivan', password=PASSWORD)

    def login(self, client, username, password=PASSWORD, **extra):
        return client.post(
            self.url, {'username': username, 'password': password, **extra}
        ).json()

    def test_login_ignores_case_and_surrounding_spaces(self, client, ivan):
        assert self.login(client, ' Ivan ')['status'] == 'success'

    def test_password_is_not_stripped(self, client, ivan):
        assert self.login(client, 'ivan', f' {PASSWORD}')['status'] == 'error'

    def test_wrong_password(self, client, ivan):
        data = self.login(client, 'ivan', 'wrong-password')
        assert data['status'] == 'error'
        assert 'Неправильное' in data['message']

    def test_pending_account_with_right_password_is_told_so(self, client):
        User.objects.create_user('pending', password=PASSWORD, is_active=False)
        data = self.login(client, 'pending')
        assert data['status'] == 'error'
        assert 'не подтверждён' in data['message']

    def test_pending_account_with_wrong_password_is_not_revealed(self, client):
        User.objects.create_user('pending', password=PASSWORD, is_active=False)
        data = self.login(client, 'pending', 'wrong-password')
        assert 'Неправильное' in data['message']

    def test_nul_character_is_an_error_not_500(self, client):
        data = self.login(client, 'iv\x00an')
        assert data['status'] == 'error'

    def test_success_returns_safe_next(self, client, ivan):
        assert self.login(client, 'ivan', next='/summary/')['next'] == '/summary/'

    @pytest.mark.parametrize('next_url', ['https://evil.example/', '//evil.example', 'javascript:alert(1)'])
    def test_unsafe_next_is_replaced_with_root(self, client, ivan, next_url):
        assert self.login(client, 'ivan', next=next_url)['next'] == '/'


class TestUserWithoutCoreSettings:
    """Пользователь, созданный мимо регистрации (createsuperuser, shell), не должен ломать страницы."""

    PAGES = ('summary', 'transactions', 'add_summary', 'add_transaction', 'change_period')

    def test_pages_open_and_defaults_are_created(self, client):
        user = User.objects.create_user('nocore', password=PASSWORD)
        client.force_login(user)
        for name in self.PAGES:
            assert client.get(reverse(f'transactions:{name}')).status_code == 200, name
        core = CoreSettings.objects.get(user=user)
        assert core.current_space.user == user
        assert core.current_space.name == 'nocore'

    def test_long_username_space_name_is_truncated(self, client):
        user = User.objects.create_user('n' * 40, password=PASSWORD)
        client.force_login(user)
        assert client.get(reverse('transactions:summary')).status_code == 200
        assert CoreSettings.objects.get(user=user).current_space.name == 'n' * 20

    def test_existing_own_space_is_reused(self, client):
        user = User.objects.create_user('nocore', password=PASSWORD)
        Space.objects.create(user=user, name='family')
        client.force_login(user)
        assert client.get(reverse('transactions:summary')).status_code == 200
        assert CoreSettings.objects.get(user=user).current_space.name == 'family'
        assert Space.objects.filter(user=user).count() == 1

    def test_export_and_period_actions_do_not_fail(self, client):
        user = User.objects.create_user('nocore', password=PASSWORD)
        client.force_login(user)
        assert client.get(reverse('export:excel')).status_code == 200
        assert client.get(reverse('transactions:apply_period') + '?period=2025_3').status_code == 302


class TestProfile:

    def test_invalid_form_does_not_change_header_name(self, user_1_client, user_1):
        """При ошибке валидации в шапке остаётся сохранённое имя, а не введённое в форму."""
        user_1.first_name = 'Старое'
        user_1.save()
        resp = user_1_client.post(reverse('users:profile'), {
            'email': 'not-an-email', 'first_name': 'Новое', 'last_name': '',
        })
        assert resp.status_code == 200
        assert resp.context['user'].first_name == 'Старое'


class TestAdminUsers:

    @pytest.fixture
    def admin_client(self, client):
        boss = User.objects.create_superuser('boss', 'boss@example.com', PASSWORD)
        client.force_login(boss)
        return client

    def test_changelist_and_add_pages_open(self, admin_client):
        assert admin_client.get(reverse('admin:users_user_changelist')).status_code == 200
        assert admin_client.get(reverse('admin:users_user_add')).status_code == 200

    def test_activate_action_confirms_registration(self, admin_client):
        pending = User.objects.create_user('pending', password=PASSWORD, is_active=False)
        resp = admin_client.post(
            reverse('admin:users_user_changelist'),
            {'action': 'activate_users', '_selected_action': [pending.pk]},
            follow=True,
        )
        assert resp.status_code == 200
        pending.refresh_from_db()
        assert pending.is_active is True
