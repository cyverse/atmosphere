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
                ('link_getting_started', models.CharField(max_length=254)),
                ('link_new_provider', models.CharField(max_length=254)),
                ('link_faq', models.CharField(max_length=254)),
                ('email_address', models.EmailField(max_length=254, null=True, blank=True)),
                ('email_header', models.TextField(null=True, blank=True)),
                ('email_footer', models.TextField(null=True, blank=True)),
            ],
            options={
                'db_table': 'email_template',
            },
        ),
        migrations.RunPython(create_template)
    ]
