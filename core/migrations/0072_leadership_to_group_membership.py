# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-10-07 15:43
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0071_provider_more_instance_actions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='leaders',
        ),
        migrations.RenameModel(
            old_name='Leadership',
            new_name='GroupMembership',
        ),
        migrations.AlterModelTable(
            name='groupmembership',
            table='group_members',
        ),
        # Part 2:
        migrations.AddField(
            model_name='groupmembership',
            name='is_leader',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='groupmembership',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='core.Group'),
        ),
        migrations.AlterField(
            model_name='groupmembership',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL),
        ),
    ]
