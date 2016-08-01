# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_update_templates_with_cyverse'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='allocation',
            unique_together=set([]),
        ),
    ]
