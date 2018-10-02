"""
Common functions used by all API test cases
"""
from urlparse import urljoin
from rest_framework import status


def reuse_instance(
    test_client, full_instance_url, machine_alias, instance_name
):
    # Launch a new one
    instance_list_resp = test_client.api_client.get(full_instance_url)
    # Ensure it worked
    test_client.assertEqual(instance_list_resp.status_code, status.HTTP_200_OK)
    test_client.assertIsNotNone(instance_list_resp.data)
    instance_id = None
    instance_ip = None
    for instance in instance_list_resp.data:
        if instance.get("machine_alias") == machine_alias:
            print 'Found potential instance, verifying it can be reused..'
            if instance.get("status") in ['active', 'running']:
                instance_id = instance.get("alias")
                instance_ip = instance.get("ip_address")
                break
            print "Cannot reuse non active instance:%s (%s)"\
                  % (instance.get("alias"), instance.get("status"))
    return (instance_id, instance_ip)


def remove_instance(test_client, instance_url, instance_alias):
    """
    Terminate the instance
    """
    new_instance_url = urljoin(instance_url, '%s/' % instance_alias)
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
