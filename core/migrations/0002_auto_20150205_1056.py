# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudAdministrator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.CharField(default=uuid.uuid4, unique=True, max_length=32, editable=False)),
                ('provider', models.ForeignKey(to='core.Provider')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'cloud_administrator',
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='allocationrequest',
            name='start_date',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 5, 17, 56, 15, 517279, tzinfo=utc)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quotarequest',
            name='start_date',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 5, 17, 56, 15, 517279, tzinfo=utc)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statustype',
            name='start_date',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 5, 17, 56, 15, 516445, tzinfo=utc)),
            preserve_default=True,
        ),
    ]
