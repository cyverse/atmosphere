#!/usr/bin/env python
import json
import logging
from optparse import OptionParser

from service_old.models import Instance
import django
django.setup()


def export_instance_tags():
    instance_tags = []
    instances = Instance.objects.all()
    added = 0
    for i in instances:
        if i.instance_tags:
            tag_json = []
            tag_list = i.instance_tags.split(',')
            for tag in tag_list:
                tag_json.append({'name': tag, 'description': ''})
            instance_tags.append({'instance': i.instance_id, 'tags': tag_json})
            added = added + 1
    logging.info('%s records exported' % added)
    return json.dumps(instance_tags)


def import_instance_tags(instance_tags_json):
    instance_tags = json.loads(instance_tags_json)
    added = 0
    skipped = 0
    for instance_tag in instance_tags:
        try:
            instance = Instance.objects.get(
                instance_id=instance_tag['instance'])
            instance.instance_tags = ','.join(
                [tag['name'] for tag in instance_tag['tags']])
            instance.save()
            added = added + 1
        except Instance.DoesNotExist as dne:
            logging.warn(
                'Could not import tags for instance <%s> - DB Record does not exist' %
                instance_tag['instance'])
            skipped = skipped + 1
    total = added + skipped
    logging.info(
        '%s Records imported. %s Records added, %s Records skipped' %
        (total, added, skipped))
    return


def main():
    (options, filenames) = parser.parse_args()
    if not filenames or len(filenames) == 0:
        print 'Missing filename'
        parser.print_help()
        return 1

    filename = filenames[0]
    if options.export:
        f = open(filename, 'w')
        json_data = export_instance_tags()
        f.write(json_data)
    else:
        f = open(filename, 'r')
        json_data = f.read()
        import_instance_tags(json_data)
    f.close()
    return

usage = "usage: %prog [command] filename"
parser = OptionParser(usage=usage)
parser.add_option(
    "--import",
    action="store_false",
    dest="export",
    help="Override the current DB with the Instance Tag JSON file provided")
parser.add_option(
    "--export",
    action="store_true",
    dest="export",
    default=True,
    help="Export the current DB instance tags to empty file provided")

if __name__ == '__main__':
    main()
