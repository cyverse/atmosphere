import os
import sys
import ansible.playbook
import ansible.runner
from ansible import callbacks
from ansible import utils


def deploy_to(ip):
    the_playbook="/root/atmosphere/service/ansible/playbooks/test_integration.yml"
    host_list="/root/atmosphere/service/ansible/hosts"
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
    inventory = ansible.inventory.Inventory(host_list=host_list)
    inventory.subset(build_name(ip))
    inventory.get_hosts()[0].vars["ansible_ssh_host"] = ip
    pb = ansible.playbook.PlayBook(
        playbook=the_playbook,
        inventory=inventory,
        stats=stats,
        callbacks=playbook_cb,
        runner_callbacks=runner_cb,
        check=True
    )
    pb.run()


def build_name(ip):
    list_of_subnet = ip.split(".")
    return "vm%s-%s" % (list_of_subnet[2], list_of_subnet[3])


if __name__ == "__main__":
    deploy_to(sys.argv[1])
