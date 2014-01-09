"""
Common functions used by all API test cases
"""
from urlparse import urljoin
from datetime import datetime
from rest_framework import status
from threepio import logger
from time import sleep

def verify_expected_output(test_client, api_out, expected_out):
    """
    Using the output from the api:
    {'key1':'val1','key2':'random_val2'}
    and the expected output:
    {'key1':'val1','key2':''}

    1. Verify that all keys in expected output appear in the api
    2. If the value for the expected output is known, the api value must match
    """
    for key in expected_out.keys():
        test_client.assertTrue(api_out.has_key(key))
        if expected_out.get(key):
            test_client.assertEqual(api_out[key], expected_out[key])

def reuse_instance(test_client, full_instance_url, machine_alias, instance_name):
    # Launch a new one
    instance_list_resp = test_client.api_client.get(full_instance_url)
    # Ensure it worked
    test_client.assertEqual(instance_list_resp.status_code,
                            status.HTTP_200_OK)
    test_client.assertIsNotNone(instance_list_resp.data)
    instance_id = None
    instance_ip = None
    for instance in instance_list_resp.data:
        if instance.get("status") in ['active','running'] and \
           instance.get("machine_alias") == machine_alias:
            instance_id = instance.get("alias")
            instance_ip = instance.get("ip_address")
            break
    return (instance_id, instance_ip)


def standup_instance(test_client, full_instance_url,
                     machine_alias, size_alias, name, 
                     delete_before=False, delete_after=False,
                     first_launch=False):
    """
    * Select a machine (Base/Random?)
    * Select a size (Smallest)
    * Launch the instance
    * Wait until the instance is 'READY'
    * Verify the instance is 'READY'
    """
    instance_id, ip_addr = reuse_instance(test_client, full_instance_url,
            machine_alias, name)
    if instance_id and ip_addr:
        print "reusing instance %s" % instance_id
        return instance_id, ip_addr
    launch_data = {
            "machine_alias":machine_alias,
            "size_alias":size_alias,
            "name":name,
            "tags":['test_instance','test','testing']}
    #Delete them all
    if delete_before:
        remove_all_instances(test_client, full_instance_url)
    if first_launch:
        launch_data['delay'] = 20*60
    # Launch a new one
    instance_launch_resp = test_client.api_client.post(full_instance_url, launch_data, format='json')
    # Ensure it worked
    test_client.assertEqual(instance_launch_resp.status_code, status.HTTP_201_CREATED)
    test_client.assertIsNotNone(instance_launch_resp.data)
    test_client.assertIsNotNone(instance_launch_resp.data.get('alias'))
    instance_id = instance_launch_resp.data['alias']
    launch_time = datetime.now()
    #Instance is launched, wait until active
    finished = False
    minutes = 1
    attempts = 0
    while not finished:
        #Attempt communication
        new_instance_url = urljoin(full_instance_url, '%s/' % instance_id)
        instance_get_resp = test_client.api_client.get(new_instance_url)
        test_client.assertIsNotNone(instance_get_resp.data)
        ip_addr = instance_get_resp.data['ip_address']
        updated_status = instance_get_resp.data['status'].lower()
        if updated_status not in ['active','running']:
            #1m, 2m, 4m, 5m, 5m, ...
            attempts += 1
            minutes = min(5, 2**minutes)
            test_client.assertNotEqual(attempts, 10,
                "Made 10 attempts to wait for an active/running instance. Giving up..")

            logger.info("Waiting for instance %s to be in active/running state"
                        ". Current status:%s. Waiting:%s minutes"
                        % (instance_id, updated_status, minutes))
            sleep(minutes * 60)
            continue
        finished = True
        #Sleep if it failed
    deploy_duration = datetime.now() - launch_time
    logger.info("Instance %s has finished deployment. Deployment time:%s"
                % (instance_id, deploy_duration))
    if delete_after:
        remove_all_instances(test_client, full_instance_url)
    return instance_id, ip_addr


def remove_instance(test_client, instance_url, instance_alias):
    """
    Terminate the instance
    """
    new_instance_url = urljoin(
            instance_url,
            '%s/' % instance_alias)
    delete_resp = test_client.api_client.delete(new_instance_url)
    test_client.assertEqual(delete_resp.status_code, status.HTTP_200_OK)

def remove_all_instances(test_client, instance_url):
    list_instance_resp = test_client.api_client.get(instance_url)
    test_client.assertEqual(list_instance_resp.status_code, status.HTTP_200_OK)
    if not list_instance_resp.data:
        return True
    for instance in list_instance_resp.data:
        remove_instance(test_client, instance_url, instance['alias'])
    return True
