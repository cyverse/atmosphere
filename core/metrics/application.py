import pickle
import collections
import numpy
import redis

from threepio import logger
from django.utils import timezone
from dateutil import rrule
from core.models import (
    Instance, InstanceStatusHistory
)


METRICS_CACHE_DURATION = 4*24*60*60  # 4 days (persist over the weekend)


def _get_summarized_application_metrics(application, force=False, read_only=False):
    metrics = collections.OrderedDict()
    redis_cache = redis.StrictRedis()
    key = "metrics-application-summary-%s" % (application.id)
    try:
        if redis_cache.exists(key) and not force:
            pickled_object = redis_cache.get(key)
            metrics = pickle.loads(pickled_object)
        elif not read_only:
            metrics = calculate_summarized_application_metrics(application)
            pickled_object = pickle.dumps(metrics)
            redis_cache.set(key, pickled_object)
            redis_cache.expire(key, METRICS_CACHE_DURATION)
    except:
        logger.exception("Unexpected errror in application metrics")
    return metrics


def calculate_summarized_application_metrics(app):
    """
    From start_date of Application to now/End-date of application
      - # forks (How many MachineRequests.Instance.source.application was this application?)
        # favorites (How many users have bookmarked this?)
        # project favorites ( How many have added to project?)
        # launches total
        # launches success
    """
    from core.models import MachineRequest
    num_forks = MachineRequest.objects.filter(status__name='completed', new_version_forked=True)\
        .filter(instance__source__providermachine__application_version__application__id=app.id).count()
    num_bookmarked = app.bookmarks.count()
    num_in_projects = app.projects.count()
    app_instances = Instance.objects.filter(source__providermachine__application_version__application__id=app.id)
    total_launched = app_instances.count()
    total_successful = app_instances.filter(instancestatushistory__status__name='active').distinct().count()
    success_pct = 0.0
    if total_launched != 0:
        success_pct = total_successful/float(total_launched) * 100

    application_metrics = {
        'forks': num_forks,
        'bookmarks': num_bookmarked,
        'projects': num_in_projects,
        'instances': {
            'total': total_launched,
            'success': total_successful,
            'percent': success_pct,
        }
    }
    return application_metrics
