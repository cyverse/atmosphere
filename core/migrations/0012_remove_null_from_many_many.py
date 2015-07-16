# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_atmosphere_user_manager_update'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocationstrategy', name='refresh_behaviors', field=models.ManyToManyField(
                to='core.RefreshBehavior', blank=True), ), migrations.AlterField(
            model_name='allocationstrategy', name='rules_behaviors', field=models.ManyToManyField(
                to='core.RulesBehavior', blank=True), ), migrations.AlterField(
            model_name='machinerequest', name='new_machine_licenses', field=models.ManyToManyField(
                to='core.License', blank=True), ), migrations.AlterField(
            model_name='project', name='applications', field=models.ManyToManyField(
                related_name='projects', to='core.Application', blank=True), ), migrations.AlterField(
            model_name='project', name='instances', field=models.ManyToManyField(
                related_name='projects', to='core.Instance', blank=True), ), migrations.AlterField(
            model_name='project', name='volumes', field=models.ManyToManyField(
                related_name='projects', to='core.Volume', blank=True), ), migrations.AlterField(
            model_name='providermachine', name='licenses', field=models.ManyToManyField(
                to='core.License', blank=True), ), ]
