# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


import uuid

def gen_uuid(apps, schema_editor, core_model, attr='uuid'):
    CoreModel = apps.get_model('core', core_model)
    # for testing
    #values_list = []
    for row in CoreModel.objects.all():
        if hasattr(row, attr) and not getattr(row, attr):
            new_uuid = str(uuid.uuid4())
            setattr(row, attr, new_uuid)
            row.save()
        #values_list.append(getattr(row, attr))
            #test_row = CoreModel.objects.get(id=row.id)
            #if not getattr(test_row, attr):
            #    raise Exception("CANNOT ASSIGN A VALUE")
    #if len(values_list) > len(set(values_list)):
    #    duplicates = set([x for x in values_list if values_list.count(x) > 1])
    #    raise Exception("LIST IS NOT UNIQUE -- %s" % duplicates)

def uuid_for_all(apps, schema_editor):
    model_key_map = {
            # UUID
            'atmosphereuser' : 'uuid',
            'allocation' : 'uuid',
            'applicationbookmark' : 'uuid',
            'bootscript' : 'uuid',
            'credential' : 'uuid',
            'group' : 'uuid',
            'identitymembership' : 'uuid',
            'instancemembership' : 'uuid',
            'instancesource' : 'uuid',
            'instancestatushistory' : 'uuid',
            'license' : 'uuid',
            'leadership' : 'uuid',
            'machinerequest' : 'uuid',
            'providercredential' : 'uuid',
            'resourcerequest' : 'uuid',
            'quota' : 'uuid',
            'size' : 'uuid',
            'statustype' : 'uuid',
            'tag' : 'uuid',
            # UUID2
            'application' : 'uuid2',
            'cloudadministrator' : 'uuid2',
            'identity' : 'uuid2',
            'machinerequest' : 'uuid2',
            'provider' : 'uuid2',
            'project' : 'uuid2',
            'resourcerequest' : 'uuid2',
    }
    for core_model, uuid_key in model_key_map.items():
        gen_uuid(apps, schema_editor, core_model, uuid_key)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_uuid_all_the_things'),
    ]

    operations = [
        migrations.RunPython(uuid_for_all, reverse_code=migrations.RunPython.noop),

    ]
