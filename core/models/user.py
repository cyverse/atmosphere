from django.contrib.auth.models import AbstractUser
from django.db import models
from threepio import logger

class AtmosphereUser(AbstractUser):
    selected_identity = models.ForeignKey('Identity', blank=True, null=True)

    def user_quota(self):
        identity = self.select_identity()
        identity_member = identity.identitymembership_set.all()[0]
        return identity_member.quota

    def select_identity(self):
        #Return previously selected identity
        if self.selected_identity:
            return self.selected_identity

        from core.models import IdentityMembership

        for group in self.group_set.all():
            membership = IdentityMembership.get_membership_for(group.name)
            if not membership:
                continue
            self.selected_identity = membership.identity
            if self.selected_identity:
                logger.debug("Selected Identity:%s" % self.selected_identity)
                self.save()
                return self.selected_identity


    def email_hash(self):
        m = md5()
        m.update(self.user.email)
        return m.hexdigest()

    class Meta:
        db_table = 'atmosphere_user'
        app_label = 'core'


