# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models.status_type


def go_back(apps, schema_editor):
    pass


def apply_data_migration(apps, schema_editor):
    MatchType = apps.get_model("core", "MatchType")
    add_match_types(MatchType)


def add_match_types(MatchType):
    MatchType.objects.get_or_create(name="BasicEmail")
    MatchType.objects.get_or_create(name="Username")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_change_table_name_machine_export_to_export_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchType', fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.RunPython(
            apply_data_migration, go_back),
        migrations.CreateModel(
            name='PatternMatch', fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pattern', models.CharField(max_length=256)),
                ('type', models.ForeignKey(to='core.MatchType')),
            ], options={
                'db_table': 'pattern_match',
            },
        ),
        migrations.AddField(
            model_name='patternmatch', name='created_by', field=models.ForeignKey(to=settings.AUTH_USER_MODEL), preserve_default=True,
        ),
        migrations.AddField(
            model_name='license', name='access_list', field=models.ManyToManyField(to='core.PatternMatch', blank=True),
        ),
    ]
