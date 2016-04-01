# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_provider_configuration(apps, schema_editor):
    Provider = apps.get_model("core", "Provider")
    ProviderConfiguration = apps.get_model("core", "ProviderConfiguration")
    providers = Provider.objects.all()
    for provider in providers:
        configuration, created = ProviderConfiguration.objects.get_or_create(provider=provider)
        # if created:
        #     print "New configuration: %s" % configuration
    return

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_add_email_template_and_helplink'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProviderConfiguration',
            fields=[
                ('provider', models.OneToOneField(related_name='configuration', primary_key=True, serialize=False, to='core.Provider')),
            ],
            options={
                'db_table': 'provider_configuration',
            },
        ),
        migrations.RunPython(create_provider_configuration)
    ]
