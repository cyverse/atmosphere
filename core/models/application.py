from django.db import models
from django.utils import timezone

class Application(models.Model):
  """
  An application is a collection of machines, where each machine represents a
  single revision, together forming a linear sequence of versions. The 
  created_by field here is used for logging purposes only; do not rely on it 
  for permissions; use ApplicationMembership instead.
  """
  name = models.CharField(max_length=256)
  private = models.BooleanField(default=False)
  featured = models.BooleanField(default=False)
  icon = models.ImageField(upload_to="machine_images", null=True, blank=True)
  created_by = models.ForeignKey('AtmosphereUser')
  start_date = models.DateTimeField(default=timezone.now)
  end_date = models.DateTimeField(null=True, blank=True)

  class Meta:
      db_table = 'application'
      app_label = 'core'

class ApplicationMembership(models.Model):
  """
  Members of a private image can view & launch its respective machines. If the
  can_modify flag is set, then members also have ownership--they can make
  changes. The unique_together field ensures just one of those states is true.
  """
  application = models.ForeignKey(Application)
  group = models.ForeignKey('Group')
  can_edit = models.BooleanField(default=False)

  class Meta:
      db_table = 'application_membership'
      app_label = 'core'
      unique_together = ('application', 'group')
