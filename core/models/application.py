from django.db import models
from django.utils import timezone

from core.models.identity import Identity
from core.models.tag import Tag

class Application(models.Model):
  """
  An application is a collection of providermachines, where each
  providermachine represents a single revision, together forming a linear
  sequence of versions. The created_by field here is used for logging only;
  do not rely on it for permissions; use ApplicationMembership instead.
  """
  uuid = models.CharField(max_length=36, unique=True)
  name = models.CharField(max_length=256)
  description = models.TextField(null=True, blank=True)
  tags = models.ManyToManyField(Tag, blank=True)
  icon = models.ImageField(upload_to="machine_images", null=True, blank=True)
  private = models.BooleanField(default=False)
  featured = models.BooleanField(default=False)
  start_date = models.DateTimeField(default=timezone.now)
  end_date = models.DateTimeField(null=True, blank=True)
  # User/Identity that created the application object
  created_by = models.ForeignKey('AtmosphereUser')
  created_by_identity = models.ForeignKey(Identity, null=True)
  
  def update(self, *args, **kwargs):
      """
      Allows for partial updating of the model
      """
      #Upload args into kwargs
      for arg in args:
          for (key, value) in arg.items():
              kwargs[key] = value
      #Update the values
      for key in kwargs.keys():
          if key == 'tags':
              if type(kwargs[key]) != list:
                  tags_list = kwargs[key].split(",")
              else:
                  tags_list = kwargs[key]
              updateTags(self, tags_list)
              continue
          setattr(self, key, kwargs[key])
      self.save()
      return self

  def __unicode__(self):
      return "%s" % (self.name,)

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
