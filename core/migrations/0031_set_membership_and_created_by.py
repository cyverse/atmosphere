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
        try:
            identity = request.created_by.identity_set.get(provider_id=provider.id)
        except:
            print "MachineRequest %s: User %s does not have identity for provider" % (request.id, request.created_by)
            identity = request.created_by.identity_set.first()
        request.membership = identity.identitymembership_set.first()
        request.status = StatusType.objects.get(name="closed")
        request.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_machine_request_inherits_base_request_attrs'),
    ]

    operations = [
        migrations.RunPython(set_membership_and_created_by)
    ]
