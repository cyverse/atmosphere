import decimal

import dateutil.parser
from django.test import TestCase

from service.allocation_logic import effective_fractional_charge_rate, fractional_charge_rate_at_date


class FractionalChargeRateTest(TestCase):
    def setUp(self):
        self.default_rates = [
            {
                'effective_date': '1970-01-01T00:00:00Z',
                'rates': {
                    'active': '1.0',
                    'suspended': '0.0',
                    'shutoff': '0.0'
                }
            }
        ]
        self.fractional_rates = [
            {
                'effective_date': '1970-01-01T00:00:00Z',
                'rates': {
                    'active': '1.0',
                    'suspended': '0.0',
                    'shutoff': '0.0'
                }
            },
            {
                'effective_date': '2018-11-12T00:00:00Z',
                'rates': {
                    'active': '1.0',
                    'suspended': '0.75',
                    'shutoff': '0.5'
                }
            },
            {
                'effective_date': '2019-11-12T00:00:00Z',
                'rates': {
                    'active': '0.9',
                    'suspended': '0.8',
                    'shutoff': '0.3',
                    'shelved': '0.1'
                }
            }
        ]

    def _calc_period(self, status_name, status_rates, start_date, end_date, expected_charge_rate):
        start_datetime = dateutil.parser.parse(start_date)
        end_datetime = dateutil.parser.parse(end_date)
        assert isinstance(expected_charge_rate, str), 'expected_charge_rate should be a string: {}'.format(
            expected_charge_rate)
        actual_charge_rate = effective_fractional_charge_rate(status_name, status_rates, start_datetime, end_datetime)
        self.assertEqual(actual_charge_rate, decimal.Decimal(expected_charge_rate))

    def _calc_sample(self, status_name, status_rates, sample_date, expected_charge_rate):
        sample_datetime = dateutil.parser.parse(sample_date)
        assert isinstance(expected_charge_rate, str), 'expected_charge_rate should be a string: {}'.format(
            expected_charge_rate)
        actual_charge_rate = fractional_charge_rate_at_date(status_name, status_rates, sample_datetime)
        self.assertEqual(actual_charge_rate, decimal.Decimal(expected_charge_rate))

    def test_default_rate_active(self):
        self._calc_period('active', self.default_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '1.0')
        self._calc_sample('active', self.default_rates, '2018-01-01T00:00:00Z', '1.0')

    def test_default_rate_suspended(self):
        self._calc_period('suspended', self.default_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('suspended', self.default_rates, '2018-01-01T00:00:00Z', '0.0')

    def test_default_rate_shutoff(self):
        self._calc_period('shutoff', self.default_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('shutoff', self.default_rates, '2018-01-01T00:00:00Z', '0.0')

    def test_default_rate_shelved(self):
        self._calc_period('shelved', self.default_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('shelved', self.default_rates, '2018-01-01T00:00:00Z', '0.0')

    def test_fractional_rate_active(self):
        self._calc_period('active', self.fractional_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '1.0')
        self._calc_period('active', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-12T00:00:00Z', '1.0')
        self._calc_period('active', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-13T00:00:00Z', '1.0')
        self._calc_period('active', self.fractional_rates, '2018-11-12T00:00:00Z', '2018-11-13T00:00:00Z', '1.0')

        self._calc_sample('active', self.fractional_rates, '2018-11-01T00:00:00Z', '1.0')
        self._calc_sample('active', self.fractional_rates, '2018-11-11T23:59:59Z', '1.0')
        self._calc_sample('active', self.fractional_rates, '2018-11-12T00:00:00Z', '1.0')
        self._calc_sample('active', self.fractional_rates, '2018-11-13T00:00:00Z', '1.0')

        self._calc_period('active', self.fractional_rates, '2019-01-01T00:00:00Z', '2019-11-01T00:00:00Z', '1.0')
        self._calc_period('active', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-12T00:00:00Z', '1.0')
        self._calc_period('active', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-13T00:00:00Z', '0.95')
        self._calc_period('active', self.fractional_rates, '2019-11-12T00:00:00Z', '2019-11-13T00:00:00Z', '0.9')

        self._calc_sample('active', self.fractional_rates, '2019-11-01T00:00:00Z', '1.0')
        self._calc_sample('active', self.fractional_rates, '2019-11-11T23:59:59Z', '1.0')
        self._calc_sample('active', self.fractional_rates, '2019-11-12T00:00:00Z', '0.9')
        self._calc_sample('active', self.fractional_rates, '2019-11-13T00:00:00Z', '0.9')

    def test_fractional_rate_suspended(self):
        self._calc_period('suspended', self.fractional_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_period('suspended', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-12T00:00:00Z', '0.0')
        self._calc_period('suspended', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-13T00:00:00Z', '0.375')
        self._calc_period('suspended', self.fractional_rates, '2018-11-12T00:00:00Z', '2018-11-13T00:00:00Z', '0.75')
        self._calc_period('suspended', self.fractional_rates, '2018-11-10T00:00:00Z', '2018-11-13T00:00:00Z', '0.25')

        self._calc_sample('suspended', self.fractional_rates, '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('suspended', self.fractional_rates, '2018-11-11T23:59:59Z', '0.0')
        self._calc_sample('suspended', self.fractional_rates, '2018-11-12T00:00:00Z', '0.75')
        self._calc_sample('suspended', self.fractional_rates, '2018-11-13T00:00:00Z', '0.75')

        self._calc_period('suspended', self.fractional_rates, '2019-01-01T00:00:00Z', '2019-11-01T00:00:00Z', '0.75')
        self._calc_period('suspended', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-12T00:00:00Z', '0.75')
        self._calc_period('suspended', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-13T00:00:00Z', '0.775')
        self._calc_period('suspended', self.fractional_rates, '2019-11-12T00:00:00Z', '2019-11-13T00:00:00Z', '0.8')
        self._calc_period('suspended', self.fractional_rates, '2019-11-10T00:00:00Z', '2019-11-13T00:00:00Z',
                          '0.7666666666666666666666666666')

        self._calc_sample('suspended', self.fractional_rates, '2019-11-01T00:00:00Z', '0.75')
        self._calc_sample('suspended', self.fractional_rates, '2019-11-11T23:59:59Z', '0.75')
        self._calc_sample('suspended', self.fractional_rates, '2019-11-12T00:00:00Z', '0.8')
        self._calc_sample('suspended', self.fractional_rates, '2019-11-13T00:00:00Z', '0.8')

    def test_fractional_rate_shutoff(self):
        self._calc_period('shutoff', self.fractional_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_period('shutoff', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-12T00:00:00Z', '0.0')
        self._calc_period('shutoff', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-13T00:00:00Z', '0.25')
        self._calc_period('shutoff', self.fractional_rates, '2018-11-12T00:00:00Z', '2018-11-13T00:00:00Z', '0.5')
        self._calc_period('shutoff', self.fractional_rates, '2018-11-10T00:00:00Z', '2018-11-13T00:00:00Z',
                          '0.1666666666666666666666666666')
        self._calc_period('shutoff', self.fractional_rates, '2018-11-08T00:00:00Z', '2018-11-13T00:00:00Z', '0.10')

        self._calc_sample('shutoff', self.fractional_rates, '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('shutoff', self.fractional_rates, '2018-11-11T23:59:59Z', '0.0')
        self._calc_sample('shutoff', self.fractional_rates, '2018-11-12T00:00:00Z', '0.5')
        self._calc_sample('shutoff', self.fractional_rates, '2018-11-13T00:00:00Z', '0.5')

        self._calc_period('shutoff', self.fractional_rates, '2019-01-01T00:00:00Z', '2019-11-01T00:00:00Z', '0.5')
        self._calc_period('shutoff', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-12T00:00:00Z', '0.5')
        self._calc_period('shutoff', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-13T00:00:00Z', '0.4')
        self._calc_period('shutoff', self.fractional_rates, '2019-11-12T00:00:00Z', '2019-11-13T00:00:00Z', '0.3')
        self._calc_period('shutoff', self.fractional_rates, '2019-11-10T00:00:00Z', '2019-11-13T00:00:00Z',
                          '0.4333333333333333333333333334')
        self._calc_period('shutoff', self.fractional_rates, '2019-11-08T00:00:00Z', '2019-11-13T00:00:00Z', '0.46')

        self._calc_sample('shutoff', self.fractional_rates, '2019-11-01T00:00:00Z', '0.5')
        self._calc_sample('shutoff', self.fractional_rates, '2019-11-11T23:59:59Z', '0.5')
        self._calc_sample('shutoff', self.fractional_rates, '2019-11-12T00:00:00Z', '0.3')
        self._calc_sample('shutoff', self.fractional_rates, '2019-11-13T00:00:00Z', '0.3')

    def test_fractional_rate_shelved(self):
        self._calc_period('shelved', self.fractional_rates, '2018-01-01T00:00:00Z', '2018-11-01T00:00:00Z', '0.0')
        self._calc_period('shelved', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-12T00:00:00Z', '0.0')
        self._calc_period('shelved', self.fractional_rates, '2018-11-11T00:00:00Z', '2018-11-13T00:00:00Z', '0.0')
        self._calc_period('shelved', self.fractional_rates, '2018-11-12T00:00:00Z', '2018-11-13T00:00:00Z', '0.0')

        self._calc_sample('shelved', self.fractional_rates, '2018-11-01T00:00:00Z', '0.0')
        self._calc_sample('shelved', self.fractional_rates, '2018-11-11T23:59:59Z', '0.0')
        self._calc_sample('shelved', self.fractional_rates, '2018-11-12T00:00:00Z', '0.0')
        self._calc_sample('shelved', self.fractional_rates, '2018-11-13T00:00:00Z', '0.0')

        self._calc_period('shelved', self.fractional_rates, '2019-01-01T00:00:00Z', '2019-11-01T00:00:00Z', '0.0')
        self._calc_period('shelved', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-12T00:00:00Z', '0.0')
        self._calc_period('shelved', self.fractional_rates, '2019-11-11T00:00:00Z', '2019-11-13T00:00:00Z', '0.05')
        self._calc_period('shelved', self.fractional_rates, '2019-11-12T00:00:00Z', '2019-11-13T00:00:00Z', '0.1')

        self._calc_sample('shelved', self.fractional_rates, '2019-11-01T00:00:00Z', '0.0')
        self._calc_sample('shelved', self.fractional_rates, '2019-11-11T23:59:59Z', '0.0')
        self._calc_sample('shelved', self.fractional_rates, '2019-11-12T00:00:00Z', '0.1')
        self._calc_sample('shelved', self.fractional_rates, '2019-11-13T00:00:00Z', '0.1')

