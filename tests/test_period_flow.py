from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from transactions.models import Summary
from transactions.services import PeriodService

pytestmark = pytest.mark.django_db(transaction=True)


def flashes(resp):
    return [str(message) for message in resp.context['messages']]


def make_summary(space, month, year, group='Продукты', kind='expense', plan='100'):
    return Summary.objects.create(
        space=space, period_month=month, period_year=year,
        type_transaction=kind, group_name=group, plan_value=Decimal(plan),
    )


class TestApplyPeriod:

    @pytest.mark.parametrize('period', [
        '2026_13', '2026_0', '0_0', '9999999999_1', '-5_-5',
        '2026_9_9', 'abc', '2019_5', '2100_1', '2026_',
    ])
    def test_invalid_period_is_rejected_and_state_kept(self, user_1_client, user_1, period):
        core = user_1.core_settings
        before = (core.current_month, core.current_year)
        resp = user_1_client.get(
            reverse('transactions:apply_period') + f'?period={period}&next=/summary/',
            follow=True,
        )
        assert resp.status_code == 200
        core.refresh_from_db()
        assert (core.current_month, core.current_year) == before
        assert flashes(resp)

    def test_valid_period_is_applied(self, user_1_client, user_1):
        resp = user_1_client.get(reverse('transactions:apply_period') + '?period=2026_9&next=/summary/')
        assert resp.status_code == 302
        core = user_1.core_settings
        core.refresh_from_db()
        assert (core.current_month, core.current_year) == (9, 2026)


class TestChangePeriodPage:

    def test_periods_are_sorted_as_dates_newest_first(self, user_1_client, owner_space):
        for year, month in [(2025, 7), (2025, 9), (2025, 10), (2025, 12), (2024, 11)]:
            make_summary(owner_space, month, year)
        resp = user_1_client.get(reverse('transactions:change_period'))
        assert [p['key'] for p in resp.context['periods']] == [
            '2025_12', '2025_10', '2025_9', '2025_7', '2024_11',
        ]
        assert resp.context['periods'][0]['label'] == 'Декабрь 2025'

    def test_current_period_is_marked(self, user_1_client, user_1, owner_space):
        make_summary(owner_space, 9, 2025)
        make_summary(owner_space, 10, 2025)
        core = user_1.core_settings
        core.current_month, core.current_year = 9, 2025
        core.save()
        resp = user_1_client.get(reverse('transactions:change_period'))
        assert [p['key'] for p in resp.context['periods'] if p['is_current']] == ['2025_9']

    def test_viewer_has_no_new_period_button(self, viewer_client, owner_space):
        make_summary(owner_space, 9, 2025)
        resp = viewer_client.get(reverse('transactions:change_period'))
        assert 'data-open-period-modal' not in resp.content.decode()

    def test_owner_has_new_period_button(self, user_1_client):
        resp = user_1_client.get(reverse('transactions:change_period'))
        assert 'data-open-period-modal' in resp.content.decode()


class TestBrokenPeriodDoesNotBreakPages:

    def test_summary_with_month_out_of_range_does_not_break_pages(self, user_1_client, owner_space):
        """Строка с месяцем 13 (мусор в БД) раньше роняла каждую страницу контекст-процессором."""
        make_summary(owner_space, 13, 2026)
        for name in ('summary', 'transactions', 'add_summary', 'change_period'):
            assert user_1_client.get(reverse(f'transactions:{name}')).status_code == 200, name
        assert user_1_client.get(reverse('users:profile')).status_code == 200


class TestCreatePeriod:

    url = reverse('transactions:create_period')

    @pytest.fixture
    def source(self, user_1, owner_space):
        core = user_1.core_settings
        first = make_summary(owner_space, core.current_month, core.current_year, 'Продукты', plan='1234.56')
        second = make_summary(owner_space, core.current_month, core.current_year, 'Аренда', plan='2000')
        return first, second

    def create(self, client, **extra):
        data = {'period_month': '1', 'period_year': '2031', 'next': '/summary/'}
        data.update(extra)
        return client.post(self.url, data, follow=True)

    def new_period(self, owner_space):
        return Summary.objects.filter(space=owner_space, period_month=1, period_year=2031)

    def test_unchecking_everything_creates_empty_period(self, user_1_client, owner_space, source):
        """«Снять все»: браузер не шлёт ни одного флажка, но шлёт маркер copy_selection."""
        resp = self.create(user_1_client, copy_selection='1')
        assert resp.status_code == 200
        assert self.new_period(owner_space).count() == 0

    def test_without_selection_marker_everything_is_copied(self, user_1_client, owner_space, source):
        self.create(user_1_client)
        assert self.new_period(owner_space).count() == 2

    def test_only_selected_summaries_are_copied(self, user_1_client, owner_space, source):
        first, _ = source
        self.create(user_1_client, copy_selection='1', copy_summary_ids=[first.pk])
        assert list(self.new_period(owner_space).values_list('group_name', flat=True)) == ['Продукты']

    def test_plan_keeps_kopecks(self, user_1_client, owner_space, source):
        first, second = source
        self.create(user_1_client, copy_selection='1', copy_summary_ids=[first.pk, second.pk])
        assert self.new_period(owner_space).get(group_name='Продукты').plan_value == Decimal('1234.56')

    def test_plan_override_accepts_comma_and_rounds_to_kopecks(self, user_1_client, owner_space, source):
        first, _ = source
        self.create(user_1_client, copy_selection='1', copy_summary_ids=[first.pk],
                    **{f'plan_value_{first.pk}': '1500,555'})
        assert self.new_period(owner_space).get().plan_value == Decimal('1500.56')

    def test_garbage_override_falls_back_to_source_plan(self, user_1_client, owner_space, source):
        first, _ = source
        self.create(user_1_client, copy_selection='1', copy_summary_ids=[first.pk],
                    **{f'plan_value_{first.pk}': 'abc'})
        assert self.new_period(owner_space).get().plan_value == Decimal('1234.56')

    def test_too_large_override_is_rejected_without_side_effects(self, user_1_client, user_1, owner_space, source):
        first, _ = source
        core = user_1.core_settings
        before = (core.current_month, core.current_year)
        resp = self.create(user_1_client, copy_selection='1', copy_summary_ids=[first.pk],
                           **{f'plan_value_{first.pk}': '99999999999'})
        assert resp.status_code == 200
        assert self.new_period(owner_space).count() == 0
        core.refresh_from_db()
        assert (core.current_month, core.current_year) == before
        assert any('велика' in message for message in flashes(resp))

    def test_new_period_modal_shows_exact_plan(self, user_1_client, source):
        content = user_1_client.get(reverse('transactions:summary')).content.decode()
        assert 'value="1234.56"' in content
        assert 'value="2000"' in content
        assert 'name="copy_selection"' in content


class TestCreatePeriodEdgeCases:

    url = reverse('transactions:create_period')

    def test_parallel_creation_conflict_switches_to_existing_period(self, user_1_client, user_1, owner_space, monkeypatch):
        """Второй из двух одновременных «создать период» упирается в уникальность статьи — не 500."""
        core = user_1.core_settings
        make_summary(owner_space, core.current_month, core.current_year)

        def conflict(*args, **kwargs):
            raise IntegrityError('duplicate key value violates unique constraint')

        monkeypatch.setattr(PeriodService, '_copy_summaries', staticmethod(conflict))
        resp = user_1_client.post(
            self.url, {'period_month': '1', 'period_year': '2031', 'next': '/summary/'}, follow=True,
        )
        assert resp.status_code == 200
        assert any('уже существует' in message for message in flashes(resp))
        core.refresh_from_db()
        assert (core.current_month, core.current_year) == (1, 2031)

    def test_maximum_plan_can_be_copied(self, user_1_client, owner_space, user_1):
        """Раньше план 9 999 999 999,99 округлялся в модалке до 10 000 000 000 и создание периода падало с 500."""
        core = user_1.core_settings
        source = make_summary(owner_space, core.current_month, core.current_year, plan='9999999999.99')
        content = user_1_client.get(reverse('transactions:summary')).content.decode()
        assert 'value="9999999999.99"' in content
        resp = user_1_client.post(self.url, {
            'period_month': '1', 'period_year': '2031', 'next': '/summary/',
            'copy_selection': '1', 'copy_summary_ids': [source.pk],
            f'plan_value_{source.pk}': '9999999999.99',
        }, follow=True)
        assert resp.status_code == 200
        assert Summary.objects.get(space=owner_space, period_month=1, period_year=2031).plan_value == Decimal('9999999999.99')


class TestNewPeriodModalDefaults:

    def test_default_month_is_based_on_the_last_existing_period(self, user_1_client, user_1, owner_space):
        """При просмотре прошлого месяца предлагался бы уже существующий период."""
        make_summary(owner_space, 10, 2026)
        make_summary(owner_space, 9, 2026, group='Аренда')
        core = user_1.core_settings
        core.current_month, core.current_year = 9, 2026
        core.save()
        content = user_1_client.get(reverse('transactions:summary')).content.decode()
        assert 'data-last-month="10"' in content
        assert 'data-last-year="2026"' in content
