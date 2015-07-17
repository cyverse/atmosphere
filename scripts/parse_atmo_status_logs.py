#!/usr/bin/env python

import csv
from datetime import datetime


def _parse_logs(filename):
    user_history = {}
    pending_instances = {}
    with open(filename, 'r') as the_file:
        csvreader = csv.reader(the_file, delimiter=',')
        for row in csvreader:
            try:
                (timestamp,
                 username,
                 instance_id,
                 machine_id,
                 size_id,
                 status_name) = row
            except:
                print 'Could not parse row:\n%s' % row
                continue
            if status_name == 'Request Received':
                pending_instances[(username, machine_id, size_id)] = row
            else:
                first_row = pending_instances.pop(
                    (username, machine_id, size_id),
                    None)
                user_instance_history = user_history.get(username, {})
                instance_history = user_instance_history.get(instance_id, [])
                if first_row:
                    instance_history.append(first_row)
                instance_history.append(row)
                user_instance_history[instance_id] = instance_history
                user_history[username] = user_instance_history
    print "Username,Instance ID, Machine ID, Size ID, Request Time, Launch Time, Networking Time, Deployment Time, Request-to-launch, launch-to-deploy"
    for username, instance_history in user_history.items():
        for instance_id, history in instance_history.items():
            request_time = None
            launch_time = None
            network_time = None
            deploy_time = None
            for row in history:
                status = row[5]
                if not request_time and 'Request Received' in status:
                    request_time = get_time(row[0])
                elif not launch_time and 'Launching Instance' in status:
                    launch_time = get_time(row[0])
                elif not network_time and 'Networking Complete' in status:
                    network_time = get_time(row[0])
                elif not deploy_time and 'Deploy Finished' in status:
                    deploy_time = get_time(row[0])
            if not launch_time or not request_time:
                total_launch_time = "N/A"
            else:
                total_launch_time = launch_time - request_time
            if not launch_time or not deploy_time:
                total_deploy_time = "N/A"
            else:
                total_deploy_time = deploy_time - launch_time
            print "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s"\
                % (username, instance_id, row[3], row[4], request_time, launch_time, network_time, deploy_time, total_launch_time, total_deploy_time)


def get_time(time_str):
    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    _parse_logs("logs/atmosphere_status.log")
