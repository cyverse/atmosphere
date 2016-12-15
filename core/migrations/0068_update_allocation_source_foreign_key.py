#Django 1.9.8 on 2016-12-15 20:21
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_add_default_renewal_strategy'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocationsource',
            name='source_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
