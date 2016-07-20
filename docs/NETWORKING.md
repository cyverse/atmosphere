# Networking in Atmosphere

Atmosphere handles networking topologies automatically for each user on an OpenStack cloud.
In order for Atmosphere to properly connect a newly launched instance to the outside world, the cloud provider must have the proper configuration. A proper configuration can be different depending on how the cloud was intended to be used.
Typically, one of these two topologies should cover your use case. As all of this software defined networking is virtual, it is assumed that there is very little difference in performance between ExternalRouter and ExternalNetwork topologies.

If successful, the result of either topology should be the same: A newly launched instance will be able to communicate (in both directions) to the outside world!

## Types of Networking Topologies
Currently there are two networking topologies used in Atmosphere:

### External Router Topology
In an external router topology, the network looks something like this:
```
    INSTANCE --> User-Subnet --> User-Network --> User Interface between network-router --> External Router --> Internet
```

In order to use an external router, your provider must have a kwarg: `router_name` or `public_routers` if there is more than one router (In which case, users will be evenly distributed across routers upon account creation).


### External Network Topology
In an external network topology, the network looks something like this:
```
    INSTANCE --> User-Subnet --> External Network --> User Interface between network-router --> User-Router --> Router-gateway --> Internet
```

In order to use an external network, your provider must have a kwarg: `external_network_name`

All user subnets will be attached to the external network. Additionally, one interfaces will be created between the external network and the user router, and another interface (Router Gateway) will connect the users router to the outside world.
