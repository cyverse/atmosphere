#!/usr/bin/env python

import csv


def _parse_logs(filename):
    user_history = {}
    pending_instances = {}
    with open(filename, 'r') as the_file:
        csvreader = csv.reader(the_file, delimiter=',')
        for row in csvreader:
            if len(row) < 6:
                continue
            (timestamp,
             username,
             instance_id,
             machine_id,
             size_id,
             status_name) = row
            if status_name == 'Request Received':
                pending_instances[(username, machine_id, size_id)] = row
    for username, instance_history in user_history.items():
        print username
        for instance_id, history in instance_history.items():
            print "---\n%s\n---" % instance_id
            for row in history:
                print "%s @ %s" % (row[5], row[0])

if __name__ == "__main__":
    _parse_logs("logs/atmosphere_status.log")
