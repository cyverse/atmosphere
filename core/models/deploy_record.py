from django.db import models, transaction, IntegrityError
from django.utils import timezone
from enumfields import Enum, EnumField


class RecordStatus(Enum):
    PENDING="PENDING"
    SUCCESS="SUCCESS"
    FAILURE="FAILURE"
    CANCELLED="CANCELLED"


class DeployRecord(models.Model):
    """
    Records a period of time during a deployment. Each deploy should have an
    associated deploy record. Each step in a deploy checks that their deploy
    record is the latest (meaning a more recent deploy has not occurred) and
    checks that their record has not been cancelled or completed.
    """

    PENDING=RecordStatus.PENDING
    SUCCESS=RecordStatus.SUCCESS
    FAILURE=RecordStatus.FAILURE
    CANCELLED=RecordStatus.CANCELLED

    instance = models.ForeignKey("Instance")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=0)
    status = EnumField(RecordStatus, default=RecordStatus.PENDING)

    def is_active(self):
        return self.end_date == None

    def conclude_with_success(self):
        self.end_date = timezone.now()
        self.status = DeployRecord.SUCCESS
        self.save()

    def conclude_with_failure(self):
        self.end_date = timezone.now()
        self.status = DeployRecord.FAILURE
        self.save()

    @classmethod
    def latest_deploy(clss, instance, status=None):
        pending_records = clss.objects.filter(instance=instance, end_date=None)
        assert pending_records.count() < 2, \
            "Multiple pending deploy records is an application error (instance {})".format(
                    instance.provider_alias)

        return pending_records.first()

    @classmethod
    def has_deployed_successfully(clss, instance):
        return clss.objects.filter(
            instance=instance, status=DeployRecord.SUCCESS).exists()

    @classmethod
    def create_record(clss, instance):
        """
        Helper which will ensure that a prior pending deploy record will be
        cancelled in favor of this record.

        Throws an IntegrityError if more than one records are created
        concurrently for an instance. It is an error for two deploy records to
        be created simultaneously. In that event, one deploy needs exit/give
        up.
        """
        now_time = timezone.now()

        last_record = clss.objects.filter(
            instance=instance).order_by('start_date').last()

        if not last_record:
            # This is the first deploy record, just create
            return clss.objects.create(instance=instance, version=0)

        # Ensure all-or-nothing behavior of enddating prior record and
        # creating a new record
        with transaction.atomic():
            clss.objects.filter(
                id=last_record.id, end_date=None).update(
                    end_date=now_time, status=DeployRecord.CANCELLED)
            return clss.objects.create(
                start_date=now_time,
                instance=instance,
                version=last_record.version + 1)

    class Meta:
        unique_together = ("instance", "version")
        db_table = "deploy_record"
        app_label = "core"
