from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save

from .allocation import TASAPIDriver, fill_user_allocation_source_for
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", 'auth.User')

def update_user_allocation_sources(sender, instance, created, **kwargs):
    user = instance
    driver = TASAPIDriver()
    fill_user_allocation_source_for(driver, user)

#FIXME: Re-add this when you have access to the XSede API
#post_save.connect(update_user_allocation_sources, sender=AUTH_USER_MODEL)

# Create your models here.
class TASAllocationReport(models.Model):
    """
    Keep track of each Allocation Report that is sent to TACC.API
    """
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='tas_reports')  # User that matches the report
    username = models.CharField(max_length=128)  # TACC_USERNAME
    project_name = models.CharField(max_length=128)  # TACC_PROJECT_NAME aka OpenStack Tenant Credential
    compute_used = models.DecimalField(max_digits=19, decimal_places=3)  # up to approximately one billion with a resolution of 10 decimal places
    queue_name = models.CharField(max_length=128, default="Atmosphere")
    resource_name = models.CharField(max_length=128, default="Jetstream")
    scheduler_id = models.CharField(max_length=128, default="use.jetstream-cloud.org")
    start_date = models.DateTimeField()  # Required
    end_date = models.DateTimeField()  # Required
    # Meta-Metrics
    tacc_api = models.CharField(max_length=512)
    # FIXME:  Save a response confirmation -instead of- success
    report_date = models.DateTimeField(blank=True, null=True)
    success = models.BooleanField(default=False)

    def send(self, use_beta=False):
        if not self.id:
            raise Exception("ERROR -- This report should be *saved* before you send it!")
        if self.success:
            raise Exception("ERROR -- This report has already been *saved*! Create a new report!")
        try:
            if use_beta:
                from atmosphere.settings.local import BETA_TACC_API_URL, BETA_TACC_API_USER, BETA_TACC_API_PASS
                driver = TASAPIDriver(BETA_TACC_API_URL, BETA_TACC_API_USER, BETA_TACC_API_PASS)
            else:
                driver = TASAPIDriver()
            success = driver.report_project_allocation(
                self.id, self.username,
		self.project_name, float(self.compute_used),
                self.start_date, self.end_date,
                self.queue_name, self.scheduler_id)
            self.success = True if success else False
            if self.success:
                self.report_date = timezone.now()
            self.save()
        except:
            return

    @property
    def cpu_count(self):
        """
        NOTE: This is currently not returning the values we expect
        Outputs: 0.999, 3.684, 8.999, etc. etc.
        Expected Outputs: 1, 3, 9, ...
        """
        hours_between = (self.end_date - self.start_date).total_seconds()/3600.0
        cpu_count = float(self.compute_used)/hours_between
        return cpu_count

    def __unicode__(self):
        """
        """
        duration = self.end_date - self.start_date
        return "%s (Username:%s Project:%s) used %s AU over the Duration:%s (%s - %s) Reported:%s" % \
            (self.user.username,
             self.username, self.project_name,
             self.compute_used, duration,
             self.end_date, self.start_date,
             self.report_date)
