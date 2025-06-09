from datetime import datetime

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestPeriods:
    url = '/api/v1/periods/'

    def test_get_years(self, client, user_2_auth_header, user_2_tg_only, many_transactions):

        response = client.get(
            self.url + 'years/',
            headers=user_2_auth_header,
        )

        years = {transaction.period_year for transaction in many_transactions}

        assert response.status_code == 200
        assert response.data == {'years': list(years)}

    @pytest.mark.parametrize(
        'year, result',
        [
            (datetime.now().year, {'months': [datetime.now().month], 'year': str(datetime.now().year)}),
            (datetime.now().year - 10, {'months': [], 'year': str(datetime.now().year - 10)}),
        ]
    )
    def test_get_months(self, client, user_2_auth_header, user_2_tg_only, many_transactions, year, result):
        response = client.get(
            self.url + f'months/?year={year}',
            headers=user_2_auth_header,
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
    def test_get_month_invalid_data(self, client, user_2_auth_header, user_2_tg_only, many_transactions, param):
        response = client.get(
            self.url + f'months/{param}',
            headers=user_2_auth_header,
        )

        assert response.status_code == 400
