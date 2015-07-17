# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import core.models.status_type
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_enforce_uniqueness'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceRequest', fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)), ('uuid', models.CharField(
                        default=uuid.uuid4, max_length=36)), ('admin_message', models.CharField(
                            default=b'', max_length=1024, blank=True)), ('start_date', models.DateTimeField(
                                default=django.utils.timezone.now)), ('end_date', models.DateTimeField(
                                    null=True, blank=True)), ('request', models.TextField()), ('description', models.CharField(
                                        default=b'', max_length=1024, blank=True)), ('allocation', models.ForeignKey(
                                            to='core.Allocation', null=True)), ('created_by', models.ForeignKey(
                                                to=settings.AUTH_USER_MODEL)), ('membership', models.ForeignKey(
                                                    to='core.IdentityMembership')), ('quota', models.ForeignKey(
                                                        to='core.Quota', null=True)), ('status', models.ForeignKey(
                                                            default=core.models.status_type.get_status_type_id, to='core.StatusType')), ], options={
                'db_table': 'resource_request', }, ), ]
