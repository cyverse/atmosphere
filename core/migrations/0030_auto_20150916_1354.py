# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_machinerequest_new_version_scripts'),
    ]

    operations = [
        migrations.AddField(
            model_name='machinerequest',
            name='admin_message',
            field=models.CharField(default=b'', max_length=1024, blank=True),
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='created_by',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='membership',
            field=models.ForeignKey(null=True, to='core.IdentityMembership'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='uuid',
            field=models.CharField(default=uuid.uuid4, max_length=36),
        ),
        migrations.AlterField(
            model_name='instance',
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='new_machine_owner',
            field=models.ForeignKey(related_name='new_image_owner', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='status',
            new_name='old_status'
        ),
        migrations.AddField(
            model_name='machinerequest',
            name='status',
            field=models.ForeignKey(null=True, to='core.StatusType'),
        )
    ]
