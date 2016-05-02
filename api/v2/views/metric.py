"""
 Instance metrics stored in graphite
"""
import json

from django.conf import settings
import redis
import requests

from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api import permissions
from core.models import Instance
from threepio import logger

# The hyper-stats service fetches metrics every minute
CACHE_DURATION = 60

VALID_FUNCTIONS = set(["perSecond"])

#: The default resolution specified
DEFAULT_RESOLUTION = 1

#: Maximum time period is only two weeks
MAXIMUM_TIME_PERIOD = 1209600

def create_request_uri(uuid, params):
    endpoint = "{server}/render/?target={target}&format={format}"
    query = "stats.*.{uuid}.{field}"
    summarize = "summarize({metric}, {resolution}, 'avg')"
    metric = query.format(uuid=uuid,field=params.get("field"))

    # Apply function to metric
    if "fun" in params:
        metric = "{}({})".format(params.get("fun"), metric)

    #: Check for default resolution
    if (params.get("res", DEFAULT_RESOLUTION) != DEFAULT_RESOLUTION and
        params.get("field") != "*"):
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

def get_metrics(self, uuid, params):
    uri = create_request_uri(uuid, params)
    r = requests.get(uri)
    if r.status_code != 200:
        raise NotFound()
    return r.json()

def get_valid_params(params):
    fields = {
        "field": "*",
        "res": DEFAULT_RESOLUTION
    }

    #: Check for a valid field
    if params.get("field") is None:
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

class MetricViewSet(GenericViewSet):

    permission_classes = (permissions.InMaintenance,
                          permissions.ApiAuthRequired)

    queryset = Instance.objects.all()

    lookup_field = 'provider_alias'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return Instance.objects.filter(created_by=self.request.user)

    def get_key(self, instance, params):
        inputs = [instance.provider_alias] + params.values()
        return ":".join(map(str, inputs))

    def retrieve(self, *args, **kwargs):
        instance = self.get_object()

        params = get_valid_params(self.request.query_params)
        key = self.get_key(instance, params)
        redis_cache = redis.StrictRedis()

        if redis_cache.exists(key):
            response = json.loads(redis_cache.get(key))
        else:
            response = get_metrics(self, instance.provider_alias, params=params)
            redis_cache.set(key, json.dumps(response))
            redis_cache.expire(key, CACHE_DURATION)

        return Response(response)
