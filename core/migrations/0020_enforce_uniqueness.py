# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_set_default_status_type'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='allocation', unique_together=set(
                [('threshold', 'delta')]),),
        migrations.AlterUniqueTogether(
            name='quota',
            unique_together=set(
                [('cpu', 'memory', 'storage', 'storage_count',
                  'suspended_count')]),),
        migrations.AlterUniqueTogether(
            name='statustype', unique_together=set(
                [('name', 'start_date')]),), ]
