# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_allow_blank_membership_AND_rename_project_links'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationversion',
            old_name='iplant_system_files',
            new_name='system_files',
        ),
        migrations.RenameField(
            model_name='machinerequest',
            old_name='iplant_sys_files',
            new_name='system_files',
        ),
    ]
