from django.core.urlresolvers import reverse
from django.test import TestCase

import unittest

from dateutil.relativedelta import relativedelta
from django.utils.timezone import datetime
import pytz

from core.tests.helpers import CoreStatusHistoryHelper, CoreInstanceHelper
# Create an instance
# build identical instance status history timings and try to add them
# It should fail and force you to do 'the right thing only'


class CoreInstanceTestCase(unittest.TestCase):

    def _get_history_manager(self, instance, *query_args, **query_kwargs):
        """
        Return instance history list
        """
        if not query_args and not query_kwargs:
            return instance.instancestatushistory_set.all()
        return instance.instancestatushistory_set.filter(
            *
            query_args,
            **query_kwargs)

    def assertZeroHistory(self, instance):
        """
        Assert that the instance has ZERO history
        """
        history_list = self._get_history_manager(instance)
        self.assertTrue(len(history_list) == 0)
        return self

    def assertNoActiveHistory(self, instance):
        """
        Assert that the instance has ZERO 'active' history
        """
        history_list = self._get_history_manager(instance, end_date=None)
        self.assertTrue(len(history_list) == 0)
        return self

    def assertOneActiveHistory(self, instance):
        """
        Assert that the instance has only ONE history
        """
        history_list = self._get_history_manager(instance, end_date=None)
        self.assertTrue(len(history_list) == 1)
        return self


class TestInstanceStatusHistory(CoreInstanceTestCase):

    def setUp(self):
        self.history_swap_every = relativedelta(minutes=30)
        self.start_time = self.begin_history = datetime(
            2015,
            1,
            1,
            tzinfo=pytz.utc)
        self.terminate_time = datetime(2015, 1, 8, tzinfo=pytz.utc)
        self.instance_helper = CoreInstanceHelper(
            "test_instance", "1234-1234-1234-1234", self.start_time)

    def test_growing_history(self):
        """
        * Create an instance
        * Fill it with history
          * active/suspended every 30m for 1 week
        * Terminate it.

        Verify that AT MOST ONE history is 'un-end-dated'
        """
        self.instance_1 = self.instance_helper.to_core_instance()
        self.assertZeroHistory(self.instance_1)
        self.history_helper = CoreStatusHistoryHelper(
            self.instance_1,
            self.begin_history)
        # Create first history for instance
        first_history = self.history_helper.first_transaction()
        self.assertOneActiveHistory(self.instance_1)
        next_start = self.begin_history + self.history_swap_every
        suspended = False
        while next_start < self.terminate_time:
            self.history_helper.set_start_date(next_start)
            self.history_helper.status_name = \
                'suspended' if suspended else 'active'
            next_history = self.history_helper.new_transaction()
            self.assertOneActiveHistory(self.instance_1)
            suspended = not suspended
            next_start = next_start + self.history_swap_every
        self.instance_1.end_date_all(self.terminate_time)
        self.assertNoActiveHistory(self.instance_1)
