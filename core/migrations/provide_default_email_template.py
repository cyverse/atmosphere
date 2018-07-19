from __future__ import unicode_literals
from django.db import migrations


def provide_default_email_template(apps, schema_editor):
    EmailTemplate = apps.get_model("core", "EmailTemplate")
    (template, created) = EmailTemplate.objects.get_or_create(pk=1)
    if created:
        template.links.create(link_key='getting-started', topic='Getting Started with a new Instance')
        template.links.create(link_key='faq', topic='Atmosphere FAQs')

class Migration(migrations.Migration):

    dependencies = [
        ('core', 'make_provider_type_unique_by_name'),
    ]

    operations = [
        migrations.RunPython(
            provide_default_email_template,
            migrations.RunPython.noop),
    ]

