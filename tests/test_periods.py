from datetime import datetime

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestPeriods:
    url = '/api/v1/users/{user_id}/periods/'

    def test_get_years(self, client, auth_header, user_2_tg_only, many_transactions):

        response = client.get(
            self.url.format(user_id=user_2_tg_only.id) + 'years/',
            headers=auth_header,
        )

        years = {transaction.period_year for transaction in many_transactions}

        assert response.status_code == 200
        assert response.data == list(years)

    @pytest.mark.parametrize(
        'year, result',
        [
            (datetime.now().year, [datetime.now().month]),
            (datetime.now().year - 10, [])
        ]
    )
    def test_get_months(self, client, auth_header, user_2_tg_only, many_transactions, year, result):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id) + f'months/?year={year}',
            headers=auth_header,
        )
        assert response.status_code == 200
        assert response.data == result

    @pytest.mark.parametrize(
        'param',
        [
            '?year=qwerty',
            '',
        ]
    )
    def test_get_month_invalid_data(self, client, auth_header, user_2_tg_only, many_transactions, param):
        response = client.get(
            self.url.format(user_id=user_2_tg_only.id) + f'months/{param}',
            headers=auth_header,
        )

        assert response.status_code == 400
