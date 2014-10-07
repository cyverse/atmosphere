#from django.db import models
#
# NOTE: These are "warlock" models, NOT django models.
import warlock

## INPUTS
allocation_schema = {
    "name":"Allocation",
    "properties": {
        "start_date" : { "type" : "string" },
        "end_date" : { "type" : "string" },
        "rules" : { "type" : "array"},
        "instances" : { "type " : "array" },
    },
}
rule_schema = {
    "name":"Rule",
    "properties": {
        "name" : { "type" : "string"},
        "type" : { "type" : "string"},
        "amount" : { "type" : "number"},
        "unit" : { "type" : "string"},
    },
}
instance_schema = {
    "name":"Instance",
    "properties": {
        "identifier": { "type": "string" },
        "provider": { "type": "integer" },
        "machine": { "type": "string" },
        "history" : { "type " : "array" },
    }
}
instance_history_schema = {
    "name":"InstanceHistory",
    "properties": {
        "start_date" : { "type" : "string" },
        "end_date" : { "type" : "string" },
        "status" : { "type" : "string" },
        "size" : { "type" : "object" },
    },
}
size_schema = {
    "name":"Size",
    "properties": {
        "id" : { "type" : "string" },
        "cpu" : {"type" : "number" },
        "ram" : {"type" : "number" },
        "disk" : {"type" : "number" },
    },
}

## OUTPUTS
instance_result_schema = {
    "name": "InstanceResult",
    "properties": {
        "used_allocation": { "type": "number" },
        "burn_rate": { "type": "number" },
    }
}
allocation_result_schema = {
    "name": "AllocationResult",
    "properties": {
        "total_allocation": { "type": "number" },
        "used_allocation": { "type": "number" },
        "remaining_allocation": { "type": "number" },
        "burn_rate": { "type": "number" },
        "time_to_zero": { "type": "string" },
        "instance_results": { "type": "array" },
    }
}
Allocation = warlock.model_factory(allocation_schema)
Rule = warlock.model_factory(rule_schema)
Instance = warlock.model_factory(instance_schema)
InstanceHistory = warlock.model_factory(instance_history_schema)
Size = warlock.model_factory(size_schema)
InstanceResult = warlock.model_factory(instance_result_schema)
AllocationResult = warlock.model_factory(allocation_result_schema)
