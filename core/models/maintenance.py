from datetime import datetime
from django.db import models


class MaintenanceRecord(models.Model):
    """
    Maintenace can be activated through the database
    """
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=256)
    message = models.TextField()
    disable_login = models.BooleanField(default=True)

    @classmethod
    def active(cls):
        now = datetime.now()
        records = []
        for r in MaintenanceRecord.objects.filter(
                start_date__lt=now,
                end_date__isnull=True):
            records.append(r)
        for r in MaintenanceRecord.objects.filter(
                start_date__lt=now,
                end_date__gt=now):
            records.append(r)
        return records

    @classmethod
    def disable_login_access(cls):
        disable_login = False
        records = MaintenanceRecord.active()
        for record in records:
            if record.disable_login:
                disable_login = True
        return disable_login

    def json(self):
        return {
            'start': self.start_date,
            'end': self.end_date,
            'title': self.title,
            'message': self.message,
        }

    def __unicode__(self):
        return '%s (Maintenance Times: %s - %s Login disabled: %s)' % (
            self.title,
            self.start_date,
            self.end_date,
            self.disable_login
        )

    class Meta:
        db_table = "maintenance_record"
        app_label = "core"
