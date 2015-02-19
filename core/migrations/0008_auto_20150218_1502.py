# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def go_back(apps, schema_editor):
    Provider = apps.get_model("core", "Provider")
    ProviderTrait = apps.get_model("core", "ProviderTrait")
    for provider in Provider.objects.all():
        if provider.dns_server_ips.filter(ip_address="8.8.8.8"):
            trait = ProviderTrait.objects.get_or_create(name="Google DNS", description="Google DNS")
            provider.traits.add(trait)
        elif provider.dns_server_ips.filter(ip_address="128.196.11.234"):
            trait = ProviderTrait.objects.get_or_create(name="iPlant DNS", description="iPlant DNS")
            provider.traits.add(trait)
        elif provider.auto_imaging:
            trait = ProviderTrait.objects.get_or_create(name="Auto-Imaging", description="Auto-Imaging")
            provider.traits.add(trait)
    return


def copy_data_to_new_models(apps, schema_editor):
    Provider = apps.get_model("core", "Provider")
    ProviderDNSServerIP = apps.get_model("core", "ProviderDNSServerIP")

    InstanceAction = apps.get_model("core", "InstanceAction")
    add_instance_actions(InstanceAction)

    for provider in Provider.objects.all():
        for trait in provider.traits.all():
            if trait.name == "Google DNS":
                get_or_create_google_dns(ProviderDNSServerIP, provider)
            elif trait.name == "iPlant DNS":
                get_or_create_iplant_dns(ProviderDNSServerIP, provider)
            elif trait.name == "Auto-Imaging":
                add_auto_imaging(provider)
    return


def add_instance_actions(InstanceAction):
    InstanceAction.objects.get_or_create(name="Start", description="""Starts an instance when it is in the 'stopped' State""")
    InstanceAction.objects.get_or_create(name="Stop", description="""Stops an instance when it is in the 'active' State""")
    InstanceAction.objects.get_or_create(name="Resume", description="""Resumes an instance when it is in the 'suspended' State""")
    InstanceAction.objects.get_or_create(name="Suspend", description="""Suspends an instance when it is in the 'active' State""")
    InstanceAction.objects.get_or_create(name="Reboot", description="""Reboots an instance when it is in ANY State""")
    InstanceAction.objects.get_or_create(name="Hard Reboot", description="""Hard Reboots an instance when it is in ANY State""")
    InstanceAction.objects.get_or_create(name="Resize", description="""Represents the Resize/Confirm_Resize/Revert_Resize operations""")
    InstanceAction.objects.get_or_create(name="Imaging", description="""Represents the ability to Image/Snapshot an instance""")


def add_auto_imaging(provider):
    provider.auto_imaging = True
    provider.save()


def get_or_create_google_dns(ProviderDNSServerIP, provider):
    ProviderDNSServerIP.objects.get_or_create(provider=provider, ip_address="8.8.8.8", order=1)
    ProviderDNSServerIP.objects.get_or_create(provider=provider, ip_address="8.8.4.4", order=2)


def get_or_create_iplant_dns(ProviderDNSServerIP, provider):
    ProviderDNSServerIP.objects.get_or_create(provider=provider, ip_address="128.196.11.233", order=1)
    ProviderDNSServerIP.objects.get_or_create(provider=provider, ip_address="128.196.11.234", order=2)
    ProviderDNSServerIP.objects.get_or_create(provider=provider, ip_address="128.196.11.235", order=3)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20150216_1237'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstanceAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProviderDNSServerIP',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_address', models.GenericIPAddressField(null=True, unpack_ipv4=True)),
                ('order', models.IntegerField()),
                ('provider', models.ForeignKey(related_name='dns_server_ips', to='core.Provider')),
            ],
            options={
                'db_table': 'provider_dns_server_ip',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProviderInstanceAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True)),
                ('instance_action', models.ForeignKey(to='core.InstanceAction')),
                ('provider', models.ForeignKey(to='core.Provider')),
            ],
            options={
                'db_table': 'provider_instance_action',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='providerdnsserverip',
            unique_together=set([('provider', 'ip_address'), ('provider', 'order')]),
        ),
        migrations.AddField(
            model_name='provider',
            name='auto_imaging',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.RunPython(copy_data_to_new_models, go_back),
        migrations.RemoveField(
            model_name='provider',
            name='traits',
        ),
        migrations.DeleteModel(
            name='Trait',
        ),
    ]
