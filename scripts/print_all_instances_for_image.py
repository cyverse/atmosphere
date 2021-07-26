import argparse
import sys


def main():

    description = ("Print instance launches for a specific image")

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('uuid', help='An image uuid')
    args = parser.parse_args()

    # Check environment
    try:
        import django
        django.setup()
        from core.models import Instance
        from django.db.models import Q
    except:
        print "\n".join(
            [
                "ERROR! This script requires a proper environment! Try:", "",
                "   export PYTHONPATH=\"/opt/dev/atmosphere:$PYTHONPATH\"",
                "   export DJANGO_SETTINGS_MODULE='atmosphere.settings'",
                "   . /opt/env/atmo/bin/activate"
            ]
        )
        sys.exit(1)

    uuid = args.uuid
    query = Q(
        source__providermachine__application_version__application__uuid=uuid
    )
    instances = Instance.objects.filter(query) \
                                .order_by('-start_date')

    print "START_DATE, UUID, NAME, USERNAME"
    for i in instances:
        start_date = str(i.start_date)
        uuid = i.provider_alias
        name = i.name
        username = i.created_by.username
        print ",".join([start_date, uuid, name, username])


if __name__ == "__main__":
    main()
