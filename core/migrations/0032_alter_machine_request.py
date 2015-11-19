# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_set_membership_and_created_by'),
    ]

    operations = [
        migrations.RenameField(
            model_name='machinerequest',
            old_name='new_version_storage_min',
            new_name='new_version_cpu_min',
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='created_by',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='membership',
            field=models.ForeignKey(to='core.IdentityMembership'),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='new_version_membership',
            field=models.ManyToManyField(to='core.Group'),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='status',
            field=models.ForeignKey(default=-1, to='core.StatusType'),
        ),
    ]
