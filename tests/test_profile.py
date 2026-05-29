import pytest
from django.test.client import Client
from django.urls import reverse

from users.forms import ProfileForm

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def user_1_with_password(user_1):
    user_1.set_password('OldPass123!')
    user_1.save()
    return user_1, 'OldPass123!'


class TestProfileView:

    url = reverse('users:profile')

    def test_profile_requires_login(self, client):
        """Анонимный пользователь редиректится на страницу логина."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert '/auth/login' in response.url or '/login' in response.url

    def test_profile_get_ok(self, user_1_client):
        """GET авторизованным юзером отдаёт 200 и кладёт нужные ключи в контекст."""
        response = user_1_client.get(self.url)
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'current_space' in response.context
        assert 'available_spaces' in response.context
        assert 'telegram_settings' in response.context

    def test_profile_get_lists_available_spaces(self, user_1_client, user_1):
        """В контексте `available_spaces` присутствует активное пространство пользователя."""
        response = user_1_client.get(self.url)
        active_space = user_1.core_settings.current_space
        spaces = list(response.context['available_spaces'])
        assert active_space in spaces

    def test_profile_get_shows_password_link_for_regular_user(
        self, user_1_client
    ):
        """У обычного пользователя на странице есть ссылка на смену пароля."""
        response = user_1_client.get(self.url)
        assert reverse('users:password_change') in response.content.decode()

    def test_profile_get_hides_password_link_for_telegram_only(
        self, user_2_tg_only
    ):
        """У Telegram-only пользователя ссылка на смену пароля скрыта."""
        client = Client()
        client.force_login(user_2_tg_only)
        response = client.get(self.url)
        assert response.status_code == 200
        assert reverse(
            'users:password_change'
        ) not in response.content.decode()

    def test_profile_post_updates_user_fields(self, user_1_client, user_1):
        """POST сохраняет email, first_name, last_name и редиректит обратно."""
        response = user_1_client.post(self.url, {
            'email': 'new@example.com',
            'first_name': 'Иван',
            'last_name': 'Петров',
        })
        assert response.status_code == 302
        assert response.url == self.url
        user_1.refresh_from_db()
        assert user_1.email == 'new@example.com'
        assert user_1.first_name == 'Иван'
        assert user_1.last_name == 'Петров'

    def test_profile_post_invalid_email_rejected(
        self, user_1_client, user_1
    ):
        """Невалидный email возвращает форму с ошибкой и не меняет данные в БД."""
        original_email = user_1.email
        response = user_1_client.post(self.url, {
            'email': 'not-an-email',
            'first_name': '',
            'last_name': '',
        })
        assert response.status_code == 200
        assert response.context['form'].errors.get('email')
        user_1.refresh_from_db()
        assert user_1.email == original_email

    def test_profile_post_cannot_change_username(
        self, user_1_client, user_1
    ):
        """POST с дополнительным полем `username` игнорируется (поля нет в форме)."""
        original_username = user_1.username
        response = user_1_client.post(self.url, {
            'email': user_1.email,
            'first_name': '',
            'last_name': '',
            'username': 'hacker',
        })
        assert response.status_code == 302
        user_1.refresh_from_db()
        assert user_1.username == original_username


class TestProfileForm:

    def _base_data(self, **overrides):
        data = {'email': '', 'first_name': '', 'last_name': ''}
        data.update(overrides)
        return data

    def test_clean_email_allows_empty(self, user_1):
        """Пустой email допустим (email необязателен у AbstractUser)."""
        form = ProfileForm(self._base_data(email=''), instance=user_1)
        assert form.is_valid(), form.errors

    def test_clean_email_allows_same_email_for_self(self, user_1):
        """Оставление собственного email не считается дубликатом."""
        form = ProfileForm(
            self._base_data(email=user_1.email), instance=user_1
        )
        assert form.is_valid(), form.errors

    def test_clean_email_allows_same_email_case_insensitive(self, user_1):
        """Свой email в другом регистре тоже валиден (`exclude(pk=self)` работает)."""
        form = ProfileForm(
            self._base_data(email=user_1.email.upper()), instance=user_1
        )
        assert form.is_valid(), form.errors

    def test_clean_email_rejects_taken_by_other(
        self, user_1, user_3_shared_space
    ):
        """Email, занятый другим пользователем, отклоняется."""
        form = ProfileForm(
            self._base_data(email=user_3_shared_space.email),
            instance=user_1,
        )
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_clean_email_rejects_taken_case_insensitive(
        self, user_1, user_3_shared_space
    ):
        """Проверка уникальности email регистронезависима (`__iexact`)."""
        form = ProfileForm(
            self._base_data(email=user_3_shared_space.email.upper()),
            instance=user_1,
        )
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_form_save_persists_fields(self, user_1):
        """После is_valid + save новые значения сохраняются в БД."""
        form = ProfileForm(
            self._base_data(
                email='persist@example.com',
                first_name='Имя',
                last_name='Фамилия',
            ),
            instance=user_1,
        )
        assert form.is_valid(), form.errors
        form.save()
        user_1.refresh_from_db()
        assert user_1.email == 'persist@example.com'
        assert user_1.first_name == 'Имя'
        assert user_1.last_name == 'Фамилия'


class TestPasswordChangeView:

    url = reverse('users:password_change')
    profile_url = reverse('users:profile')

    def test_password_change_requires_login(self, client):
        """Анонимный пользователь не имеет доступа к смене пароля (редирект)."""
        response = client.get(self.url)
        assert response.status_code == 302

    def test_password_change_get_ok(self, user_1_client):
        """GET авторизованным юзером отдаёт 200 и содержит форму в контексте."""
        response = user_1_client.get(self.url)
        assert response.status_code == 200
        assert 'form' in response.context

    def test_password_change_post_success(self, user_1_with_password):
        """Валидная смена пароля редиректит на профиль и обновляет пароль в БД."""
        user, old_password = user_1_with_password
        new_password = 'NewPass456!'
        client = Client()
        client.force_login(user)
        response = client.post(self.url, {
            'old_password': old_password,
            'new_password1': new_password,
            'new_password2': new_password,
        })
        assert response.status_code == 302
        assert response.url == self.profile_url
        user.refresh_from_db()
        assert user.check_password(new_password)
        assert not user.check_password(old_password)

    def test_password_change_post_wrong_old_password(
        self, user_1_with_password
    ):
        """Неверный старый пароль возвращает форму с ошибкой и не меняет пароль."""
        user, old_password = user_1_with_password
        client = Client()
        client.force_login(user)
        response = client.post(self.url, {
            'old_password': 'WrongOldPassword!',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        assert response.status_code == 200
        assert response.context['form'].errors
        user.refresh_from_db()
        assert user.check_password(old_password)


class TestTopbarUserName:

    url = reverse('users:profile')

    def test_topbar_shows_first_name_when_set(self, user_1_client, user_1):
        """В topbar показывается имя, если оно задано."""
        user_1.first_name = 'Иван'
        user_1.save()
        response = user_1_client.get(self.url)
        assert 'Иван' in response.content.decode()

    def test_topbar_falls_back_to_username(self, user_1_client, user_1):
        """Без имени в topbar показывается логин."""
        assert user_1.first_name == ''
        response = user_1_client.get(self.url)
        assert user_1.username in response.content.decode()
