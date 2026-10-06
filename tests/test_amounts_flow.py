import threading
from decimal import Decimal

import pytest
from django.db import connection, connections
from django.test import Client
from django.urls import reverse

from transactions.amounts import AmountError, parse_amount
from transactions.models import LinkedUserToSpace, Summary, Transaction

pytestmark = pytest.mark.django_db(transaction=True)


def flashes(resp):
    return [str(message) for message in resp.context['messages']]


class TestParseAmount:

    @pytest.mark.parametrize('raw, expected', [
        ('100', '100.00'),
        ('100,5', '100.50'),
        ('1 000,50', '1000.50'),
        ('1 000.5', '1000.50'),
        ('0,005', '0.01'),
        ('9999999999.99', '9999999999.99'),
        ('  7  ', '7.00'),
    ])
    def test_valid(self, raw, expected):
        assert parse_amount(raw) == Decimal(expected)

    @pytest.mark.parametrize('raw, code', [
        ('', 'invalid'), ('abc', 'invalid'), ('NaN', 'invalid'), ('Infinity', 'invalid'),
        ('-Infinity', 'invalid'), ('1e500', 'too_large'), ('10000000000', 'too_large'),
        ('9999999999.995', 'too_large'), ('-5', 'negative'), ('0', 'zero'), ('0,004', 'zero'),
    ])
    def test_invalid(self, raw, code):
        with pytest.raises(AmountError) as error:
            parse_amount(raw)
        assert error.value.code == code

    def test_options(self):
        assert parse_amount('-5', allow_negative=True) == Decimal('-5.00')
        assert parse_amount('0', allow_zero=True) == Decimal('0.00')


@pytest.fixture
def summary(user_1, owner_space):
    core = user_1.core_settings
    return Summary.objects.create(
        space=owner_space, period_month=core.current_month, period_year=core.current_year,
        type_transaction='expense', group_name='Продукты', plan_value=Decimal('100'),
    )


class TestAddTransaction:

    url = reverse('transactions:add_transaction')

    def add(self, client, value, description='', group='Продукты'):
        return client.post(self.url, {
            'type_transaction': 'expense', 'group_name': group,
            'value_transaction': value, 'description': description,
        }, follow=True)

    @pytest.mark.parametrize('value', [
        'NaN', 'Infinity', '-Infinity', '1e20', '10000000000', '', 'abc', '0', '0,001', '0.004',
    ])
    def test_invalid_amount_is_rejected_without_changes(self, user_1_client, summary, value):
        resp = self.add(user_1_client, value)
        assert resp.status_code == 200
        assert Transaction.objects.count() == 0
        summary.refresh_from_db()
        assert summary.fact_value == 0
        assert flashes(resp)

    @pytest.mark.parametrize('value, expected', [
        ('10,5', '10.50'), ('1 000,50', '1000.50'), ('-5', '-5.00'), ('0,005', '0.01'),
    ])
    def test_valid_amount_updates_fact(self, user_1_client, summary, value, expected):
        self.add(user_1_client, value)
        summary.refresh_from_db()
        assert summary.fact_value == Decimal(expected)
        assert Transaction.objects.get().value_transaction == Decimal(expected)

    def test_facts_accumulate(self, user_1_client, summary):
        for _ in range(3):
            self.add(user_1_client, '1,10')
        summary.refresh_from_db()
        assert summary.fact_value == Decimal('3.30')
        assert Transaction.objects.count() == 3

    def test_fact_overflow_is_rejected(self, user_1_client, summary):
        summary.fact_value = Decimal('9999999999.00')
        summary.save()
        resp = self.add(user_1_client, '5')
        assert Transaction.objects.count() == 0
        assert any('превысит' in message for message in flashes(resp))

    def test_control_characters_are_removed_from_description(self, user_1_client, summary):
        self.add(user_1_client, '1', 'a\x0bb\x00c')
        assert Transaction.objects.get().description == 'abc'

    def test_unknown_group_is_rejected(self, user_1_client, summary):
        resp = self.add(user_1_client, '1', group='Нет такой')
        assert Transaction.objects.count() == 0
        assert any('не найдена' in message for message in flashes(resp))


class TestAddSummary:

    url = reverse('transactions:add_summary')

    def create(self, client, name='Кафе', plan='100', kind='expense'):
        return client.post(self.url, {
            'type_transaction': kind, 'group_name': name, 'plan_value': plan,
        }, follow=True)

    @pytest.mark.parametrize('plan', ['NaN', 'Infinity', '-1', 'abc', '', '1e20', '10000000000'])
    def test_invalid_plan_is_rejected(self, user_1_client, plan):
        resp = self.create(user_1_client, plan=plan)
        assert resp.status_code == 200
        assert Summary.objects.count() == 0
        assert flashes(resp)

    def test_plan_is_rounded_to_kopecks(self, user_1_client):
        self.create(user_1_client, plan='12,345')
        assert Summary.objects.get().plan_value == Decimal('12.35')

    def test_duplicate_message_does_not_mention_type(self, user_1_client, summary):
        resp = self.create(user_1_client, name='Продукты', kind='income')
        assert Summary.objects.count() == 1
        message = next(m for m in flashes(resp) if 'уже существует' in m)
        assert 'для этого типа' not in message

    def test_control_characters_are_removed_from_name(self, user_1_client):
        self.create(user_1_client, name='Ка\x00фе')
        assert Summary.objects.get().group_name == 'Кафе'

    def test_recreated_summary_takes_fact_from_existing_transactions(self, user_1_client, summary):
        TestAddTransaction().add(user_1_client, '40')
        user_1_client.post(reverse('transactions:delete_summary', args=[summary.pk]))
        assert not Summary.objects.filter(pk=summary.pk).exists()
        assert Transaction.objects.count() == 1  # операции переживают статью
        self.create(user_1_client, name='Продукты', plan='100')
        assert Summary.objects.get().fact_value == Decimal('40.00')


class TestSummariesPageRendering:

    def test_numbers_in_data_attributes_are_not_localized(self, user_1_client, summary):
        """«112500,74» в data-атрибуте parseFloat читает как 112500 — копейки пропадают."""
        summary.fact_value = Decimal('112500.74')
        summary.plan_value = Decimal('150000.00')
        summary.save()
        content = user_1_client.get(reverse('transactions:add_summary')).content.decode()
        assert 'data-fact="112500.74"' in content
        assert 'data-plan="150000.00"' in content
        assert '112500,74' not in content

    def test_groups_page_shows_grouped_amounts_with_kopecks(self, user_1_client, summary):
        summary.fact_value = Decimal('112500.74')
        summary.plan_value = Decimal('150000.00')
        summary.save()
        content = user_1_client.get(reverse('transactions:add_summary')).content.decode()
        assert '<strong>112\xa0500,74</strong> / 150\xa0000 ₽' in content

    def test_transactions_page_amounts_are_not_localized(self, user_1_client, summary):
        TestAddTransaction().add(user_1_client, '1234,56')
        content = user_1_client.get(reverse('transactions:transactions')).content.decode()
        assert 'data-amount="1234.56"' in content

    def test_delete_uses_data_confirm_instead_of_inline_handler(self, user_1_client, summary):
        summary.group_name = "Ко's"
        summary.save()
        content = user_1_client.get(reverse('transactions:add_summary')).content.decode()
        assert 'onsubmit=' not in content
        assert 'data-confirm="Удалить статью «Ко&#x27;s»?"' in content

    def test_delete_confirm_mentions_transactions_that_stay(self, user_1_client, summary):
        TestAddTransaction().add(user_1_client, '1')
        content = user_1_client.get(reverse('transactions:add_summary')).content.decode()
        assert 'Операции статьи (1) останутся в журнале.' in content

    def test_viewer_has_no_delete_buttons(self, viewer_client, owner_space, user_1):
        core = user_1.core_settings
        Summary.objects.create(
            space=owner_space, period_month=core.current_month, period_year=core.current_year,
            type_transaction='expense', group_name='Продукты', plan_value=1,
        )
        content = viewer_client.get(reverse('transactions:add_summary')).content.decode()
        assert 'data-confirm' not in content
        assert 'cat-action-btn' not in content


class TestMemberIdValidation:

    @pytest.mark.parametrize('route', ['change_member_role', 'remove_member'])
    @pytest.mark.parametrize('value', ['abc', '', '1e3', '99999999999999999999999'])
    def test_non_numeric_member_id_is_an_error_not_500(self, user_1_client, owner_space, make_user, route, value):
        member = make_user('member_x')
        LinkedUserToSpace.objects.create(space=owner_space, linked_user=member)
        resp = user_1_client.post(
            reverse(f'transactions:{route}', args=[owner_space.pk]),
            {'linked_user_id': value, 'role': 'edit_space', 'next': '/users/profile/'},
            follow=True,
        )
        assert resp.status_code == 200
        assert 'Участник не найден.' in flashes(resp)
        assert LinkedUserToSpace.objects.filter(space=owner_space, linked_user=member).exists()


@pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='блокировка строки (select_for_update) есть только в PostgreSQL',
)
class TestConcurrentTransactions:

    def test_parallel_posts_do_not_lose_updates(self, user_1, summary):
        """Параллельные добавления не должны перезаписывать fact_value друг друга."""
        workers = 8
        barrier = threading.Barrier(workers)
        statuses = []

        def worker():
            try:
                client = Client()
                client.force_login(user_1)
                barrier.wait()
                response = client.post(reverse('transactions:add_transaction'), {
                    'type_transaction': 'expense', 'group_name': 'Продукты', 'value_transaction': '1',
                })
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker) for _ in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert statuses == [302] * workers
        assert Transaction.objects.count() == workers
        summary.refresh_from_db()
        assert summary.fact_value == Decimal(workers)


class TestApplySpaceInput:

    @pytest.mark.parametrize('value', ['abc', '', '-1', '0', '1e3', '99999999999999999999999'])
    def test_bad_space_id_is_an_error_not_500(self, user_1_client, user_1, owner_space, value):
        resp = user_1_client.post(
            reverse('transactions:apply_space'), {'space': value, 'next': '/summary/'}, follow=True,
        )
        assert resp.status_code == 200
        assert 'Пространство не найдено.' in flashes(resp)
        user_1.core_settings.refresh_from_db()
        assert user_1.core_settings.current_space == owner_space
