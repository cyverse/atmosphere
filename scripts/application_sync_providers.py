#!/usr/bin/env python

import application_to_provider

description = """
This script effects a one-way synchronization of Applications (a.k.a. images)
from a master Provider to one or more minion Providers.

Given master Provider X, minion Providers [Y, Z]
For each Application A
    For each ApplicationVersion AV of application A
        If AV has a ProviderMachine + InstanceSource on X
            For each minion Provider MProv
                If AV does NOT have a ProviderMachine + InstanceSource on MProv
                    Run application_to_provider for A to MProv

"""