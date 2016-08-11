# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def try_update_iplant_to_cyverse(apps, schema_editor):
    try:
        EmailTemplate = apps.get_model("core", "EmailTemplate")
        template = EmailTemplate.objects.get(email_address='support@iplantcollaborative.org')
        template.email_address = u'support@cyverse.org'
        template.email_footer = u'CyVerse Atmosphere Team'
        template.save()
    except:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0061_allow_non_unique_allocation_pair'),
    ]

    operations = [
        migrations.RunPython(try_update_iplant_to_cyverse),
        migrations.AlterField(
            model_name='emailtemplate',
            name='email_address',
            field=models.EmailField(default=b'support@cyverse.org', max_length=254),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='email_footer',
            field=models.TextField(default=b'CyVerse Atmosphere Team'),
        ),
    ]
