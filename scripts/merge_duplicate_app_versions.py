#!/usr/bin/env python
import django
django.setup()

from core.models import Application
from django.db.models import Q, Count
from core.models.application_version import merge_duplicated_app_versions, ApplicationVersion

def main():
    broken_apps = Application.objects.annotate(num_versions=Count('versions')).filter(num_versions__gt=1)
    for app in broken_apps:
        app_versions = app.versions.order_by('start_date')
        master = app_versions.first()
        copies = app_versions.all()[1:]
        merge_duplicated_app_versions(master, copies)

if __name__ == "__main__":
    main()
