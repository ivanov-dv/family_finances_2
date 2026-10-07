import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from django.urls import reverse
from django.views.defaults import permission_denied

from transactions.models import Summary, Transaction

pytestmark = pytest.mark.django_db(transaction=True)


class TestErrorPages:

    def test_404_is_styled_and_lets_anonymous_log_in(self, client):
        resp = client.get('/no-such-page/')
        assert resp.status_code == 404
        content = resp.content.decode()
        assert 'Страница не найдена' in content
        assert '<title>FF — Страница не найдена</title>' in content
        assert 'loginModal' in content

    def test_404_for_authenticated_keeps_navigation(self, user_1_client):
        resp = user_1_client.get('/no-such-page/')
        assert resp.status_code == 404
        assert 'id="sidebar"' in resp.content.decode()

    def test_403_page(self, user_1):
        request = RequestFactory().get('/')
        request.user = user_1
        resp = permission_denied(request, Exception('no'))
        assert resp.status_code == 403
        assert 'Нет доступа' in resp.content.decode()

    def test_csrf_failure_page_is_localized(self):
        resp = Client(enforce_csrf_checks=True).post('/users/ajax-login/', {'username': 'a', 'password': 'b'})
        assert resp.status_code == 403
        content = resp.content.decode()
        assert 'Запрос отклонён' in content
        assert 'DEBUG' not in content

    def test_500_page_is_standalone(self):
        content = render_to_string('500.html')
        assert 'Ошибка сервера' in content
        assert '{%' not in content and '<link' not in content


class TestDashboardOrder:

    def test_articles_are_sorted_by_name_and_do_not_jump_after_a_change(self, user_1_client, user_1, owner_space):
        core = user_1.core_settings
        for name in ('Яблоки', 'арбузы', 'Бананы'):
            Summary.objects.create(
                space=owner_space, period_month=core.current_month, period_year=core.current_year,
                type_transaction='expense', group_name=name, plan_value=100,
            )

        def names():
            resp = user_1_client.get(reverse('transactions:summary'))
            return [e['g'] for e in resp.context['expenses_json']]

        assert names() == ['арбузы', 'Бананы', 'Яблоки']          # без учёта регистра
        Summary.objects.filter(group_name='Яблоки').update(fact_value=5)   # свежее изменение не поднимает статью наверх
        assert names() == ['арбузы', 'Бананы', 'Яблоки']


class TestTitles:

    @pytest.mark.parametrize('name, expected', [
        ('summary', 'Дашборд'),
        ('transactions', 'Операции'),
        ('add_summary', 'Статьи бюджета'),
        ('add_transaction', 'Новая операция'),
        ('change_period', 'Период'),
    ])
    def test_transaction_pages_have_own_title(self, user_1_client, name, expected):
        content = user_1_client.get(reverse(f'transactions:{name}')).content.decode()
        assert f'<title>FF — {expected}</title>' in content

    @pytest.mark.parametrize('name, expected', [
        ('users:profile', 'Профиль'),
        ('users:password_change', 'Смена пароля'),
    ])
    def test_user_pages_have_own_title(self, user_1_client, name, expected):
        content = user_1_client.get(reverse(name)).content.decode()
        assert f'<title>FF — {expected}</title>' in content

    def test_login_page_has_title_and_brand(self, client):
        content = client.get(reverse('login')).content.decode()
        assert '<title>FF — Вход</title>' in content
        assert '<span>FF</span>' in content

    def test_main_landmark_is_present(self, user_1_client):
        assert '<main class="content">' in user_1_client.get(reverse('transactions:summary')).content.decode()


class TestAssets:

    def test_favicon_exists_and_is_linked(self, client):
        # Статика проекта лежит в src/static и копируется в раздачу отдельно от collectstatic.
        assert (settings.BASE_DIR / 'static' / 'img' / 'favicon.svg').is_file()
        assert 'img/favicon.svg' in client.get('/').content.decode()

    def test_theme_is_applied_before_first_paint(self, client):
        content = client.get('/').content.decode()
        head = content[:content.index('</head>')]
        assert "localStorage.getItem('ff-theme')" in head
        assert 'data-bs-theme' in head


class TestViewerSeesNoForms:

    def test_viewer_gets_notice_instead_of_add_form(self, viewer_client):
        content = viewer_client.get(reverse('transactions:add_transaction')).content.decode()
        assert 'id="add-form"' not in content
        assert 'Только просмотр' in content

    def test_user_without_space_gets_notice(self, no_space_client):
        content = no_space_client.get(reverse('transactions:add_transaction')).content.decode()
        assert 'id="add-form"' not in content
        assert 'Нет активного пространства' in content

    def test_owner_and_editor_get_the_form(self, user_1_client, editor_client):
        for client in (user_1_client, editor_client):
            content = client.get(reverse('transactions:add_transaction')).content.decode()
            assert 'id="add-form"' in content
            assert 'data-once' in content


class TestMessageStyles:

    def test_info_message_is_not_styled_as_error(self, user_1_client, user_1, owner_space):
        core = user_1.core_settings
        Summary.objects.create(
            space=owner_space, period_month=core.current_month, period_year=core.current_year,
            type_transaction='expense', group_name='Продукты', plan_value=1,
        )
        resp = user_1_client.post(reverse('transactions:create_period'), {
            'period_month': core.current_month, 'period_year': core.current_year, 'next': '/summary/',
        }, follow=True)
        content = resp.content.decode()
        assert 'alert-msg alert-info' in content
        assert 'alert-error' not in content.split('<main')[1]

    def test_success_and_error_keep_their_styles(self, user_1_client):
        ok = user_1_client.post(reverse('transactions:create_space'), {'name': 'новое', 'next': '/summary/'}, follow=True)
        assert 'alert-msg alert-success' in ok.content.decode()
        bad = user_1_client.post(reverse('transactions:create_space'), {'name': '', 'next': '/summary/'}, follow=True)
        assert 'alert-msg alert-error' in bad.content.decode()


class TestHeadings:

    @pytest.mark.parametrize('name', [
        'transactions:summary', 'transactions:transactions', 'transactions:add_summary',
        'transactions:add_transaction', 'transactions:change_period',
        'users:profile', 'users:password_change',
    ])
    def test_authenticated_pages_have_exactly_one_h1(self, user_1_client, name):
        content = user_1_client.get(reverse(name)).content.decode()
        assert content.count('<h1') == 1

    @pytest.mark.parametrize('url', ['/', '/auth/login/', '/no-such-page/'])
    def test_public_pages_have_exactly_one_h1(self, client, url):
        assert client.get(url).content.decode().count('<h1') == 1


class TestOperationsGroupFilter:

    def add(self, user, space, group, value='1'):
        core = user.core_settings
        Transaction.objects.create(
            space=space, author=user, period_month=core.current_month, period_year=core.current_year,
            type_transaction='expense', group_name=group, value_transaction=value,
        )

    def test_select_lists_distinct_groups_sorted_and_escaped(self, user_1_client, user_1, owner_space):
        for group in ('Яблоки', 'арбузы', 'Яблоки', '"><i>'):
            self.add(user_1, owner_space, group)
        resp = user_1_client.get(reverse('transactions:transactions'))
        assert resp.context['group_names'] == ['"><i>', 'арбузы', 'Яблоки']
        html = resp.content.decode()
        select = html.split('id="groupFilter"')[1].split('</select>')[0]
        assert select.count('<option value=') == 4   # + «Все статьи»
        assert '"><i>' not in html.replace('&quot;&gt;&lt;i&gt;', '')

    def test_no_select_for_a_single_group(self, user_1_client, user_1, owner_space):
        self.add(user_1, owner_space, 'Продукты')
        assert 'id="groupFilter"' not in user_1_client.get(reverse('transactions:transactions')).content.decode()
