# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_add_end_date_identitymembership_instance_atmosphereuser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationversionmembership',
            name='application_version',
            field=models.ForeignKey(db_column=b'application_version_id', default=uuid.uuid4, to='core.ApplicationVersion'),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name='applicationversionmembership',
            old_name='application_version',
            new_name='image_version',
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
    ]
