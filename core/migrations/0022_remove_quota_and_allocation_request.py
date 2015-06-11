# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_add_resourcerequest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='allocationrequest',
            name='allocation',
        ),
        migrations.RemoveField(
            model_name='allocationrequest',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='allocationrequest',
            name='membership',
        ),
        migrations.RemoveField(
            model_name='allocationrequest',
            name='status',
        ),
        migrations.RemoveField(
            model_name='quotarequest',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='quotarequest',
            name='membership',
        ),
        migrations.RemoveField(
            model_name='quotarequest',
            name='quota',
        ),
        migrations.RemoveField(
            model_name='quotarequest',
            name='status',
        ),
        migrations.DeleteModel(
            name='AllocationRequest',
        ),
        migrations.DeleteModel(
            name='QuotaRequest',
        ),
    ]
