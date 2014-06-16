#!/usr/bin/env python
import argparse

import libcloud.security

from core.models import Provider

from service.driver import get_admin_driver

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False

_admin_driver = None
_all_instances = None
_sizes = None


def _get_provider():
    return Provider.objects.get(id=4)


def _set_admin_driver():
    global _admin_driver
    _admin_driver = get_admin_driver(_get_provider())


def _set_all_instances():
    if not _admin_driver:
        _set_admin_driver()
    global _all_instances
    if not _all_instances:
        _all_instances = _admin_driver.list_all_instances()


def _set_sizes():
    if not _admin_driver:
        _set_admin_driver()
    global _sizes
    _sizes = _admin_driver.list_sizes()


def _get_sizes():
    if not _sizes:
        _set_sizes()
    return _sizes


def _get_all_instances():
    if not _all_instances:
        _set_all_instances()
    return _all_instances


def _get_hypervisor():
    if not _admin_driver:
        _set_admin_driver()
    return _admin_driver._connection.ex_hypervisor_statistics()


def _get_host(instance):
    try:
        return instance.extra["object"]["OS-EXT-SRV-ATTR:host"]
    except:
        return None


def _get_nodes(nodes=None):
    if not nodes:
        nodes = set(_get_host(i)
                    for i in _get_all_instances())
        nodes.add("Total")
        nodes.add("Hypervisor")
    else:
        nodes = {n for n in nodes}
        if "None" in nodes:
            nodes.remove("None")
            nodes.add(None)
    return nodes


def _get_empty_node_map(nodes):
    return {node: {'cpus': 0,
                   'ram': 0,
                   'disk': 0} for node in _get_nodes(nodes)}


def _get_size_map():
    return {size.id: size for size in _get_sizes()}


def _get_size(size_id):
    return _get_size_map().get(size_id)


def _acc_resources(node_map, size):
    node_map["Total"]["cpus"] += size.cpu
    node_map["Total"]["ram"] += size.ram
    node_map["Total"]["disk"] += size.disk


def _node_resources(status=None, nodes=None):
    """
    Return the resource usage per node.

    ``status`` parameter is a list of instance statuses. If it's defined
    it'll filter by that list. Otherwise it'll return all statuses.
    """
    if not status:
        status = _get_status()
    node_map = _get_empty_node_map(nodes)
    for i in _get_all_instances():
        if i.extra["status"] in status:
            node = i.extra["object"]["OS-EXT-SRV-ATTR:host"]
            if not node_map.has_key(node):
                continue
            size = _get_size(i.size.id)
            node_map[node]["cpus"] += size.cpu
            node_map[node]["ram"] += size.ram
            node_map[node]["disk"] += size.disk
            if "Total" in node_map.keys():
                _acc_resources(node_map, size)
    if "Hypervisor" in node_map.keys():
        node_map["Hypervisor"] = _get_hypervisor()
    return node_map


def _get_status():
    status = set()
    [status.add(i.extra['status']) for i in _get_all_instances()]
    return status


def _node_resources_pretty_print(resources):
    s = ""
    for k, v in resources.items():
        if k not in ["Total", "Hypervisor"]:
            s += "%s: \n\tcpus: %s\n\tram: %s\n\n" % (k, v['cpus'], v['ram'])
    if resources.get("Total"):
        v = resources["Total"]
        s += "%s: \n\tcpus: %s\n\tram: %s\n\n" % ("Total", v['cpus'], v['ram'])
    if resources.get("Hypervisor"):
        h = resources["Hypervisor"]
        s += "Hypervisor\n"
        for k,v in sorted(h.items()):
            s += "\t%s: %s\n" % (k, v)
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", help="Filter by instance statuses. (comma separated)")
    parser.add_argument("--nodes", help="Filter by OpenStack compute nodes. (comma separated)")
    parser.add_argument("--python", help="Print Python data structures.", action="store_true")
    args = parser.parse_args()
    status = None
    nodes = None
    if args.status:
        status = set(args.status.split(","))
    if args.nodes:
        nodes = set(args.nodes.split(","))
    resources = _node_resources(status=status, nodes=nodes)
    if args.python:
        print resources
    else:
        print _node_resources_pretty_print(resources)


if __name__ == "__main__":
    main()
