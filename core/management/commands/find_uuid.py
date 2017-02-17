import os
from django.core.management.base import BaseCommand
import django.db.models.base
from subprocess import call
import core.models

class Command(BaseCommand):
    help = 'Custom manage.py command to start celery.'

    def add_arguments(self, parser):
        parser.add_argument("needle", type=str, help="The uuid/field that you are looking for")

    def handle(self, *args, **options):
        needle = options.get('needle')
        if not needle:
            print "Exception: Missing value to search for"
            return
        field_type, result = find_string_in_models(core.models, needle)
        if not result:
            print "Exception:Could not find value %s in any of the imports from %s (Using %s field types)" % (needle, core.models, field_type)
        else:
            human_field_type = "UUID" if field_type == 'uuidfield' else 'String'
            if hasattr(result, 'get_source_class'):
                result = result.get_source_class
            print "%s <%s> belongs to %s %s" % (human_field_type, needle, str(result.__class__), result)

def find_string_in_models(import_base, needle):
    for modelKey in import_base.__dict__.keys():
     if 'pyc' not in modelKey:
         modelCls = getattr(import_base, modelKey)
         if type(modelCls) != django.db.models.base.ModelBase:
             continue
         for field in modelCls._meta.get_fields():
             field_name = field.name
             field_type = str(modelCls._meta.get_field(field_name).get_internal_type()).lower()
             if field_type in ['uuidfield','charfield']:
                 res = modelCls.objects.filter(**{field_name:needle})
                 if res:
                     return field_type, res.last()
    return (None, None)
