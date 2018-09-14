"""
 Instance metrics stored in graphite
"""
import json

from django.conf import settings
import redis
import requests

from rest_framework.exceptions import NotFound

from threepio import logger

# The hyper-stats service fetches metrics every minute
CACHE_DURATION = 60

VALID_FUNCTIONS = set(["perSecond"])

#: The default resolution specified
DEFAULT_RESOLUTION = 1

#: Maximum time period is only two weeks
MAXIMUM_TIME_PERIOD = 1209600


def request_instance_metrics(uuid, params):
    uri = create_request_uri(uuid, params)
    r = requests.get(uri)
    if r.status_code != 200:
        raise NotFound()
    return r.json()


def create_request_uri(uuid, params):
    endpoint = "{server}/render/?target={target}&format={format}"
    query = "stats.*.{uuid}.{field}"
    summarize = "summarize({metric}, {resolution}, 'avg')"
    metric = query.format(uuid=uuid, field=params.get("field"))

    # Apply function to metric
    if "fun" in params:
        metric = "{}({})".format(params.get("fun"), metric)

    #: Check for default resolution
    if (
        params.get("res", DEFAULT_RESOLUTION) != DEFAULT_RESOLUTION
        and params.get("field") != "*"
    ):
        res = '"{}min"'.format(params["res"])

        target = summarize.format(metric=metric, resolution=res)
    else:
        target = metric

    fields = {
        "server": settings.METRIC_SERVER,
        "target": target,
        "format": "json"
    }

    request_uri = endpoint.format(**fields)

    #: (Optional) specify the window
    if "from" in params:
        request_uri = "{}&from={}".format(request_uri, params["from"])

    if "until" in params:
        request_uri = "{}&until={}".format(request_uri, params["until"])

    logger.info("metrics endpoint: " + request_uri)
    return request_uri


def params_to_fields(params):
    fields = {"field": "*", "res": DEFAULT_RESOLUTION}

    #: Check for a valid field
    if getattr(params, "field", None) is None:
        return fields

    fields["field"] = params["field"]

    #: Determine if the data should be summarized
    try:
        resolution = int(params["res"])
        size = int(params["size"])
        if "until" in params and params["until"]:
            fields["from"] = params["from"]
            fields["until"] = params["until"]
        else:
            period = resolution * 60 * size
            if period < MAXIMUM_TIME_PERIOD:
                fields["from"] = "-{}s".format(period)
                fields["res"] = resolution

        #: (Optional) Check for a valid function
        if params.get("fun", "") in VALID_FUNCTIONS:
            fields["fun"] = params["fun"]
    except:
        pass
    return fields


def _to_instance_key(instance, fields):
    inputs = [instance.provider_alias] + fields.values()
    return ":".join(map(str, inputs))


def get_instance_metrics(instance, params=None):
    fields = params_to_fields(params)
    key = _to_instance_key(instance, fields)
    redis_cache = redis.StrictRedis()
    instance_metrics = {}
    try:
        if redis_cache.exists(key):
            instance_metrics = json.loads(redis_cache.get(key))
        else:
            instance_metrics = request_instance_metrics(
                instance.provider_alias, params=params
            )
            redis_cache.set(key, json.dumps(instance_metrics))
            redis_cache.expire(key, CACHE_DURATION)
    except Exception:
        logger.exception("Failed to retrieve metrics")
    return instance_metrics
