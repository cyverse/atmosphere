# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    _ = EmailTemplate.objects.get_or_create()  # One and done
    return

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_rename_to_system_files'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('link_getting_started', models.CharField(max_length=254, default=b"https://pods.iplantcollaborative.org/wiki/display/atmman/Using+Instances")),
                ('link_new_provider', models.CharField(max_length=254, default=b"https://pods.iplantcollaborative.org/wiki/display/atmman/Changing+Providers")),
                ('link_faq', models.CharField(max_length=254, default=b'')),
                ('email_address', models.EmailField(max_length=254, default=b'support@iplantcollaborative.org')),
                ('email_header', models.TextField(default=b'')),
                ('email_footer', models.TextField(default=b'iPlant Atmosphere Team')),
            ],
            options={
                'db_table': 'email_template',
            },
        ),
        migrations.RunPython(create_template)
    ]
