# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_quota_and_allocation_field_to_requests'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('application', models.ForeignKey(to='core.Application')),
                ('tag', models.ForeignKey(to='core.Tag')),
            ],
            options={
                'db_table': 'application_tags',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InstanceTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instance', models.ForeignKey(to='core.Instance')),
                ('tag', models.ForeignKey(to='core.Tag')),
            ],
            options={
                'db_table': 'instance_tags',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instance', models.ForeignKey(to='core.Instance')),
                ('project', models.ForeignKey(to='core.Project')),
            ],
            options={
                'db_table': 'project_instances',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectVolume',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.ForeignKey(to='core.Project')),
                ('volume', models.ForeignKey(to='core.Volume')),
            ],
            options={
                'db_table': 'project_volumes',
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='application',
            name='tags',
            field=models.ManyToManyField(to='core.Tag', through='core.ApplicationTag', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='project',
            name='instances',
            field=models.ManyToManyField(related_name='projects', null=True, through='core.ProjectInstance', to='core.Instance', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='project',
            name='volumes',
            field=models.ManyToManyField(related_name='projects', null=True, through='core.ProjectVolume', to='core.Volume', blank=True),
            preserve_default=True,
        ),
    ]
