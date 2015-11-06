# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_update_fields_application_version_identity_memberships_and_no_default_statustype')
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationthreshold',
            old_name='storage_min',
            new_name='cpu_min',
        ),
    ]
