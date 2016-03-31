# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    _ = EmailTemplate.objects.get_or_create()  # One and done
    return

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
        'link_key': 'getting-started',
        'topic': 'Getting Started with a new Instance',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Using+Instances'
    },
    {
        'link_key': 'new-provider',
        'topic': 'Getting Started with a new Provider',
        'href': 'https://pods.iplantcollaborative.org/wiki/display/atmman/Changing+Providers'
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
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    template = EmailTemplate.objects.first()
    for link in INITIAL_LINKS:
        help_link, _ = HelpLink.objects.get_or_create(**link)
        template.links.add(help_link)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_rename_to_system_files'),
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
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('links', models.ManyToManyField(related_name='email_templates', to='core.HelpLink')),
                ('email_address', models.EmailField(max_length=254, default=b'support@iplantcollaborative.org')),
                ('email_header', models.TextField(default=b'')),
                ('email_footer', models.TextField(default=b'iPlant Atmosphere Team')),
            ],
            options={
                'db_table': 'email_template',
            },
        ),
        migrations.RunPython(create_template),
        migrations.RunPython(add_help_links)
    ]
