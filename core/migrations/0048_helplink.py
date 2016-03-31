# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

INITIAL_LINKS = [
    {
        'link_key': 'default',
        'topic': 'Atmosphere Manual',
        'href': 'https://pods.iplantcollaborative.org/wiki/x/Iaxm'
    },
    {
        'link_key': 'toc',
        'topic': 'Atmosphere Manual Table of Contents',
        'href': 'https://pods.iplantcollaborative.org/wiki/x/Iaxm'
    },
    {
        'link_key': 'forums',
        'topic': 'Atmosphere User Forums',
        'href': 'http://ask.iplantcollaborative.org/questions/scope:all/sort:activity-desc/tags:Atmosphere/page:1/'
    },
    {
        'link_key': 'faq',
        'topic': 'Atmosphere FAQs',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Atmosphere+FAQs'
    },
    {
        'link_key': 'vnc-viewer',
        'topic': 'Using VNC Viewer to Connect to an Atmosphere VM',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Using+VNC+Viewer+to+Connect+to+an+Atmosphere+VM'
    },
    {
        'link_key': 'request-image',
        'topic': 'Requesting an Image of an Instance',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Requesting+an+Image+of+an+Instance'
    },
    {
        'link_key': 'instances',
        'topic': 'Using Instances',
        'href': 'https://pods.iplantcollaborative.org/wiki/x/Blm'
    },
    {
        'link_key': 'instance-launch',
        'topic': 'Launching a new Instance',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Launching+a+New+Instance'
    },
    {
        'link_key': 'volumes',
        'topic': 'Attaching / Detaching Volumes',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Attaching+and+Detaching+Volumes'
    },
]


def add_help_links(apps, schema_editor):
    HelpLink = apps.get_model("core", "HelpLink")
    db_alias = schema_editor.connection.alias
    HelpLink.objects.using(db_alias).bulk_create([
        HelpLink(
            topic=l['topic'],
            link_key=l['link_key'],
            href=l['href'])
        for l in INITIAL_LINKS
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_add_email_template'),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('link_key', models.CharField(max_length=256)),
                ('topic', models.CharField(max_length=256)),
                ('context', models.TextField(default=b'', null=True, blank=True)),
                ('href', models.TextField()),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RunPython(add_help_links)
    ]
