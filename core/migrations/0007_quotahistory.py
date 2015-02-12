# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_change_fields_as_not_null'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuotaHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_name', models.CharField(max_length=255)),
                ('operation', models.CharField(default=b'UPDATE', max_length=255, choices=[(b'CREATE', b'The field has been created.'), (b'UPDATE', b'The field has been updated.'), (b'DELETED', b'The field has been deleted.')])),
                ('current_value', models.TextField()),
                ('previous_value', models.TextField()),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('quota', models.ForeignKey(related_name='history', to='core.Quota')),
            ],
            options={
                'db_table': 'quota_history',
            },
            bases=(models.Model,),
        ),
    ]
