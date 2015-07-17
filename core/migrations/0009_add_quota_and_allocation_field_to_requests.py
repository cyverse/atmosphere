# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core',
         '0008_instance_actions_and_migrate_provider_trait_to_dns_and_auto_imaging'),
    ]

    operations = [
        migrations.AddField(
            model_name='allocationrequest',
            name='allocation',
            field=models.ForeignKey(to='core.Allocation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quotarequest',
            name='quota',
            field=models.ForeignKey(to='core.Quota', null=True),
            preserve_default=True,
        ),
    ]
