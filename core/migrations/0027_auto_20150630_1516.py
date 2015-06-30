# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_remove_redundant_fields_machine_request_and_version'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='applicationversion',
            unique_together=set([('application', 'name')]),
        ),
        migrations.AlterModelTable(
            name='applicationversion',
            table='application_version',
        ),
    ]
