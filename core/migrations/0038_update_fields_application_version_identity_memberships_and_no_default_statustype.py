# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_add_end_date_identitymembership'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationversionmembership',
            name='image_version',
            field=models.ForeignKey(db_column=b'application_version_id', default=-1, to='core.ApplicationVersion'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='identitymembership',
            name='identity',
            field=models.ForeignKey(related_name='identity_memberships', to='core.Identity'),
        ),
        migrations.AlterField(
            model_name='identitymembership',
            name='member',
            field=models.ForeignKey(related_name='identity_memberships', to='core.Group'),
        ),
        migrations.AlterField(
            model_name='machinerequest',
            name='status',
            field=models.ForeignKey(to='core.StatusType'),
        ),
        migrations.AlterField(
            model_name='resourcerequest',
            name='status',
            field=models.ForeignKey(to='core.StatusType'),
        ),
        migrations.AlterUniqueTogether(
            name='applicationversionmembership',
            unique_together=set([('image_version', 'group')]),
        ),
        migrations.RemoveField(
            model_name='applicationversionmembership',
            name='application_version',
        ),
    ]
