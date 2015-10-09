# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type
import uuid

def set_membership_and_created_by(apps, schema_editor):
    MachineRequest = apps.get_model("core", "MachineRequest")
    StatusType = apps.get_model("core", "StatusType")

    requests = MachineRequest.objects.all()
    for request in requests:
        request.created_by = request.new_machine_owner
        provider = request.new_machine_provider
        # Make sure Identity exists..
        try:
            identity = request.created_by.identity_set.get(provider_id=provider.id)
        except:
            identity = request.created_by.identity_set.first()
        # Make sure IdentityMembership exists..
        try:
            membership = identity.identitymembership_set.first()
            if not membership:
                raise Exception("")
        except:
            print "MachineRequest %s: %s is missing identity membership for provider %s" % (request.id, request.created_by.username, provider.location),
            member = request.created_by.group_set.first()
            membership =  member.identitymembership_set.first()
            print "Used membership on Provider %s instead" % (membership.identity.provider.location,)
        request.membership = membership
        request.status = StatusType.objects.get(name="closed")
        request.save()
        ### For debugging
        #request = MachineRequest.objects.get(id=request.id)
        #if not request.membership:
        #    import ipdb;ipdb.set_trace()
        #    raise Exception("You should not be here!")

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_machine_request_inherits_base_request_attrs'),
    ]

    operations = [
        migrations.RunPython(set_membership_and_created_by)
    ]
