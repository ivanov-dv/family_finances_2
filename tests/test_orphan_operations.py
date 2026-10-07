"""Операции переживают удаление статьи (связь по совпадению полей): журнал их показывает с пометкой «без статьи»,
а при повторном создании статьи с тем же названием они возвращаются в отчёт."""
from decimal import Decimal

import pytest
from django.urls import reverse

from transactions.models import Summary, Transaction

pytestmark = pytest.mark.django_db(transaction=True)

BADGE = 'class="orphan-badge"'


@pytest.fixture
def summary(user_1, owner_space):
    core = user_1.core_settings
    return Summary.objects.create(
        space=owner_space, period_month=core.current_month, period_year=core.current_year,
        type_transaction='expense', group_name='Продукты', plan_value=Decimal('1000'),
    )


@pytest.fixture
def operation(user_1_client, summary):
    resp = user_1_client.post(reverse('transactions:add_transaction'), {
        'type_transaction': 'expense', 'group_name': 'Продукты', 'value_transaction': '250,50', 'description': 'хлеб',
    })
    assert resp.status_code == 302
    return Transaction.objects.get()


def journal(client):
    return client.get(reverse('transactions:transactions'))


def delete_summary(client, summary):
    return client.post(reverse('transactions:delete_summary', args=[summary.pk]))


class TestOrphanMarker:

    def test_operation_of_existing_summary_is_not_marked(self, user_1_client, operation):
        resp = journal(user_1_client)
        assert BADGE not in resp.content.decode()
        assert [t.orphan for t in resp.context['transactions']] == [False]

    def test_deleted_summary_leaves_marked_operation_in_the_journal(self, user_1_client, summary, operation):
        delete_summary(user_1_client, summary)
        assert Transaction.objects.count() == 1
        resp = journal(user_1_client)
        assert resp.content.decode().count(BADGE) == 1
        assert [t.orphan for t in resp.context['transactions']] == [True]

    def test_recreated_summary_takes_fact_from_operations_and_clears_the_marker(self, user_1_client, summary, operation):
        delete_summary(user_1_client, summary)
        user_1_client.post(reverse('transactions:add_summary'), {
            'type_transaction': 'expense', 'group_name': 'Продукты', 'plan_value': '2000',
        })
        assert Summary.objects.get().fact_value == Decimal('250.50')
        assert BADGE not in journal(user_1_client).content.decode()

    def test_same_name_of_other_type_does_not_hide_the_marker(self, user_1_client, user_1, owner_space, summary, operation):
        """Статья — это пара (тип, название): доходная «Продукты» не заменяет расходную."""
        delete_summary(user_1_client, summary)
        core = user_1.core_settings
        Summary.objects.create(
            space=owner_space, period_month=core.current_month, period_year=core.current_year,
            type_transaction='income', group_name='Продукты', plan_value=Decimal('1'),
        )
        assert journal(user_1_client).content.decode().count(BADGE) == 1

    def test_group_name_in_the_hint_is_escaped(self, user_1_client, user_1, owner_space):
        core = user_1.core_settings
        Transaction.objects.create(
            space=owner_space, author=user_1, period_month=core.current_month, period_year=core.current_year,
            type_transaction='expense', group_name='"><b>x</b>', value_transaction=Decimal('1'),
        )
        html = journal(user_1_client).content.decode()
        assert BADGE in html
        assert '"><b>x</b>' not in html and '&quot;&gt;&lt;b&gt;x&lt;/b&gt;' in html

    def test_confirmation_before_deletion_warns_about_operations(self, user_1_client, summary, operation):
        html = user_1_client.get(reverse('transactions:add_summary')).content.decode()
        assert 'Операции статьи (1) останутся в журнале' in html
