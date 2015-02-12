#!/usr/bin/env python
import subprocess
import sys


class PerformanceData:
    def __init__(self):
        self.data = {}

    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self):
        variables = []
        for k, v in self.data.iteritems():
            variables.append("%s=%s" % (k, v))
        return " ".join(variables)

if __name__ == "__main__":
    vmstat = subprocess.Popen(["vmstat", "1", "2"], stdout=subprocess.PIPE)
    tail = subprocess.Popen(["tail", "-n1"], stdout=subprocess.PIPE, stdin=vmstat.stdout)
    line, _ = tail.communicate()
    result = [int(x) for x in line.split()]
    metrics = {
        'procs':  {
            'waiting':  result[0],
            'uninterruptible':  result[1]
        },
        'memory':  {
            'swap_used':  result[2],
            'free':  result[3],
            'buffers':  result[4],
            'cache':  result[5]
        },
        'swap':  {
            'in':  result[6],
            'out':  result[7]
        },
        'io':  {
            'received':  result[8],
            'sent':  result[9]
        },
        'system':  {
            'interrupts_per_second':  result[10],
            'context_switches_per_second':  result[11]
        },
        'cpu':  {
            'user':  result[12],
            'system':  result[13],
            'idle':  result[14],
            'waiting':  result[15]
        }
    }

    perfdata = PerformanceData()
    for parent, children in metrics.iteritems():
        for child, value in children.iteritems():
            perfdata["%s.%s" % (parent, child)] = value
    print "OK | %s" % perfdata
    sys.exit(0)