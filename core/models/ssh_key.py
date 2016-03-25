from django.db import models

from threepio import logger

from core.models import AtmosphereUser

from uuid import uuid4

class SSHKey(models.Model):

    name = models.CharField(max_length=256)
    uuid = models.CharField(max_length=36, unique=True, default=uuid4)
    pub_key = models.TextField()
    atmo_user = models.ForeignKey(AtmosphereUser)

    def __unicode__(self):
        return "%s - %s Key:%s" %\
            (self.atmo_user, self.name, self.pub_key)

    class Meta:
        db_table = "ssh_key"
        app_label = "core"

def get_user_ssh_keys(username):
    user = AtmosphereUser.objects.get(username=username)
    return SSHKey.objects.filter(atmo_user=user)
