# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def do_nothing(apps, schema_editor):
    pass


def create_new_behaviors_and_strategies(apps, schema_editor):
    CountingBehavior = apps.get_model("core", "CountingBehavior")
    RefreshBehavior = apps.get_model("core", "RefreshBehavior")
    RulesBehavior = apps.get_model("core", "RulesBehavior")
    Provider = apps.get_model("core", "Provider")
    AllocationStrategy = apps.get_model("core", "AllocationStrategy")

    # Strategy #1 - Count from first to end of month, refresh on the first
    counting_strategy_1, _ = CountingBehavior.objects.get_or_create(
        name="1 Month - Calendar Window")
    refresh_strategy_1, _ = RefreshBehavior.objects.get_or_create(
        name="First of the Month")

    # Strategy #2 - Count UP for one month, starting at (& refreshing at) the
    # anniversary
    counting_strategy_2, _ = CountingBehavior.objects.get_or_create(
        name="1 Month - Calendar Window - Anniversary")
    refresh_strategy_2, _ = RefreshBehavior.objects.get_or_create(
        name="Anniversary Date")
    # Rules that will be applied by default
    rules = []
    rule, _ = RulesBehavior.objects.get_or_create(
        name="Ignore non-active status")
    rules.append(rule)
    rule, _ = RulesBehavior.objects.get_or_create(name="Multiply by Size CPU")
    rules.append(rule)

    for provider in Provider.objects.all():
        new_strategy, _ = AllocationStrategy.objects.get_or_create(
            provider=provider, counting_behavior=counting_strategy_1)
        new_strategy.refresh_behaviors.add(refresh_strategy_1)
        for rule in rules:
            new_strategy.rules_behaviors.add(rule)
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_change_fields_as_not_null'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllocationStrategy', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ], options={
                'db_table': 'allocation_strategy', }, bases=(
                        models.Model,), ), migrations.CreateModel(
                            name='CountingBehavior', fields=[
                                ('id', models.AutoField(
                                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('name', models.CharField(
                                        max_length=255)), ], options={
                                            'db_table': 'counting_behavior', }, bases=(
                                                models.Model,), ), migrations.CreateModel(
                                                    name='RefreshBehavior', fields=[
                                                        ('id', models.AutoField(
                                                            verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('name', models.CharField(
                                                                max_length=255)), ], options={
                                                                    'db_table': 'refresh_behavior', }, bases=(
                                                                        models.Model,), ), migrations.CreateModel(
                                                                            name='RulesBehavior', fields=[
                                                                                ('id', models.AutoField(
                                                                                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('name', models.CharField(
                                                                                        max_length=255)), ], options={
                                                                                            'db_table': 'rules_behavior', }, bases=(
                                                                                                models.Model,), ), migrations.AddField(
                                                                                                    model_name='allocationstrategy', name='counting_behavior', field=models.ForeignKey(
                                                                                                        to='core.CountingBehavior'), preserve_default=True, ), migrations.AddField(
                                                                                                            model_name='allocationstrategy', name='provider', field=models.OneToOneField(
                                                                                                                to='core.Provider'), preserve_default=True, ), migrations.AddField(
                                                                                                                    model_name='allocationstrategy', name='refresh_behaviors', field=models.ManyToManyField(
                                                                                                                        to='core.RefreshBehavior', null=True, blank=True), preserve_default=True, ), migrations.AddField(
                                                                                                                            model_name='allocationstrategy', name='rules_behaviors', field=models.ManyToManyField(
                                                                                                                                to='core.RulesBehavior', null=True, blank=True), preserve_default=True, ), migrations.RunPython(
                                                                                                                                    create_new_behaviors_and_strategies, do_nothing)]
