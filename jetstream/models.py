from django.db import models
from django.conf import settings
from django.utils import timezone

from .allocation import report_project_allocation
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", 'auth.User')


# Create your models here.
class TASAllocationReport(models.Model):
    """
    Keep track of each Allocation Report that is sent to TACC.API
    """
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='tas_reports')  # User that matches the report
    username = models.CharField(max_length=128)  # TACC_USERNAME
    project_name = models.CharField(max_length=128)  # TACC_PROJECT_NAME aka OpenStack Tenant Credential
    compute_used = models.DecimalField(max_digits=19, decimal_places=10)  # up to approximately one billion with a resolution of 10 decimal places
    queue_name = models.CharField(max_length=128)
    resource_name = models.CharField(max_length=128, default="Jetstream")
    scheduler_id = models.CharField(max_length=128)
    start_date = models.DateTimeField(auto_now_add=True)  # Required
    end_date = models.DateTimeField()  # Required
    # Meta-Metrics
    tacc_api = models.CharField(max_length=512)
    # FIXME:  Save a response confirmation -instead of- success
    report_date = models.DateTimeField(blank=True, null=True)
    success = models.BooleanField(default=False)

    def send_report(self):
        if not self.id:
            raise Exception("ERROR -- This report should be *saved* before you send it!")
        if self.success:
            raise Exception("ERROR -- This report has already been *saved*! Create a new report!")
        try:
            success = report_project_allocation(
                self.username, self.project_name, float(self.compute_used),
                self.start_date, self.end_date,
                self.queue_name, self.scheduler_id,
                self.resource_name, self.tacc_api)
            self.success = True if success else False
            if self.success:
                self.report_date = timezone.now()
            self.save()
        except:
            # self.success = False
            raise

    def __unicode__(self):
        """
        """
        return "%s (Username:%s Project:%s) used %s AU - Reported:%s" % \
            (self.user.username, self.username, self.project_name,
             self.compute_used, self.report_date)
