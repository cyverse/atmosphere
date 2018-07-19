from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError
from threading import Thread
import uuid

from core.models import InstanceStatusHistory, InstanceStatus
from api.tests.factories import InstanceFactory, InstanceHistoryFactory


class InstanceStatusHistoryTestCase(TestCase):
    def setUp(self):
        self.instance = InstanceFactory.create()
        InstanceHistoryFactory.create(instance=self.instance)

    def test_unique_history_version(self):
        """
        Each instance history pairing must have a unique version, otherwise an exception is
        thrown

        The version acts as an optimistic lock and prevents duplicate
        histories from being created
        """
        ish = InstanceStatusHistory.latest_history(self.instance)
        with self.assertRaises(IntegrityError):
            InstanceHistoryFactory.create(
                instance=self.instance, version=ish.version)


# This test case requires a TransactionTestCase because each test is /not/ run
# inside a db transaction, allowing for each thread to see the changes of
# other threads
class InstanceStatusHistoryConcurrentTestCase(TransactionTestCase):
    def test_concurrent_history_update(self):
        """
        InstanceStatusHistory.update_history should not raise an exception,
        when concurrent requests occur
        """
        self.instance = InstanceFactory.create()
        InstanceHistoryFactory.create(instance=self.instance)

        def target():
            # We use a unique status, because update_history ignores duplicate
            # status updates
            unique_status = str(uuid.uuid4())
            InstanceStatusHistory.update_history(self.instance, unique_status,
                                                 "")

        # Spawn 20 threads each trying to uniquely update an instance's status
        threads = [Thread(target=target) for _ in xrange(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        histories = InstanceStatusHistory.objects.filter(
            instance=self.instance)

        # 20 unique history updates plus an initial history, should result
        # in a history of 21 length
        self.assertEqual(histories.count(), 21)

        # Assert that histories agree in ordering by their start_date and
        # end_date
        date_histories = histories.order_by('start_date').values_list('id', flat=True)
        version_histories = histories.order_by('version').values_list('id', flat=True)
        self.assertListEqual(list(date_histories), list(version_histories))

        # Assert that the end_date of one is the start_date of another
        for hist, next_hist in pairwise(histories.order_by('start_date')):
            self.assertEqual(hist.end_date, next_hist.start_date)


def pairwise(iterable):
    it = iter(iterable)
    a = next(it, None)

    for b in it:
        yield (a, b)
        a = b

