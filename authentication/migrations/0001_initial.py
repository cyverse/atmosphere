# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Token',
            fields=[
                ('key', models.CharField(max_length=128, serialize=False, primary_key=True)),
                ('api_server_url', models.CharField(max_length=256)),
                ('remote_ip', models.CharField(max_length=128, null=True, blank=True)),
                ('user_agent', models.TextField(null=True, blank=True)),
                ('issuedTime', models.DateTimeField(auto_now_add=True)),
                ('expireTime', models.DateTimeField(null=True, blank=True)),
                ('user', models.ForeignKey(related_name='auth_token', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'auth_token',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProxy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=128, null=True, blank=True)),
                ('proxyIOU', models.CharField(max_length=128)),
                ('proxyTicket', models.CharField(max_length=128)),
                ('expiresOn', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'db_table': 'auth_userproxy',
                'verbose_name_plural': 'user proxies',
            },
            bases=(models.Model,),
        ),
    ]
