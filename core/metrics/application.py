import pickle
import collections
import numpy
import redis

from threepio import logger
from django.db.models import (
        Avg, ExpressionWrapper,
        F, Q, fields)
from django.utils import timezone
from dateutil import rrule
from core.models import (
    Instance, InstanceStatusHistory
)


METRICS_CACHE_DURATION = 4*24*60*60  # 4 days (persist over the weekend)


def get_application_metrics(application, now_time=None, read_only=False):
    """
    Skip image metrics on end-dated applications
    Otherwise look through the cache to find application metrics
    """
    metrics = {}
    if application.end_date:
        return metrics
    metrics = _get_application_metrics(application, interval=rrule.DAILY, now_time=now_time, read_only=read_only)
    metrics = _get_application_metrics(application, interval=rrule.WEEKLY, now_time=now_time, read_only=read_only)
    metrics = _get_application_metrics(application, interval=rrule.MONTHLY, now_time=now_time, read_only=read_only)
    return metrics


def _get_application_metrics(application, interval=rrule.MONTHLY, day_limit=120,
                             now_time=None, force=False, read_only=False):
    metrics = collections.OrderedDict()
    if not interval:
        interval = rrule.MONTHLY
    redis_cache = redis.StrictRedis()
    key = "metrics-application-%s-interval-%s-limited-to-%s" % (application.id, rrule.FREQNAMES[interval], day_limit)
    try:
        if redis_cache.exists(key) and not force:
            pickled_object = redis_cache.get(key)
            metrics = pickle.loads(pickled_object)
        elif not read_only:
            metrics = calculate_application_metrics(application, interval, day_limit, now_time=now_time)
            pickled_object = pickle.dumps(metrics)
            redis_cache.set(key, pickled_object)
            redis_cache.expire(key, METRICS_CACHE_DURATION)
    except:
        logger.exception("Unexpected errror in application metrics")
    return metrics


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


def calculate_summarized_application_metrics(application):
    """
    From start_date of Application to now/End-date of application
      - # forks (How many MachineRequests.Instance.source.application was this application?)
        # favorites (How many users have bookmarked this?)
        # project favorites ( How many have added to project?)
        # launches total
        # launches success
    """
    from core.models import MachineRequest, Instance
    num_forks = MachineRequest.objects.filter(status__name='completed', num_version_forked=True)\
        .filter(instance__source__providermachine__application_version__application__id=app.id).count()
    num_bookmarked = app.bookmarks.count()
    num_in_projects = app.projects.count()
    app_instances = Instance.objects.filter(source__providermachine__application_version__application__id=app.id)
    total_launched = app_instances.count()
    total_successful = app_instances.filter(instancestatushistory__status__name='active').distinct().count()
    success_pct = total_successful/float(total_launched) * 100

    application_metrics = {
        'forks': num_forks,
        'bookmarks': num_bookmarks,
        'projects': num_in_projects,
        'instances': {
            'total': total_launched,
            'success': total_successful,
            'percent': success_pct,
        }
    }
    return application_metrics


# Alternative calculation method, drilling down per-version rather than per-application.
def calculate_detailed_application_metrics(application, interval=rrule.MONTHLY):
    """
    From start_date of Application to now/End-date of application
      - Create a timeseries by splitting by 'interval'
      - Query for metrics datapoints
      - Return the timeseries + datapoints
    """
    now_time = timezone.now()
    the_beginning = application.start_date
    the_end = application.end_date or now_time
    application_metrics = {}
    for version in application.versions.all():
        per_version_metrics = calculate_application_version_metrics(
            version, the_beginning, the_end, interval=interval)
        application_metrics[version.name] = per_version_metrics
    return application_metrics


def calculate_application_version_metrics(version, start_date, end_date, interval=rrule.MONTHLY):
    timeseries = _generate_time_series(start_date, end_date, interval)
    per_version_metrics = collections.OrderedDict()
    for idx, ts in enumerate(timeseries):
        interval_start = ts
        if idx == len(timeseries)-1:
            interval_end = end_date
        else:
            interval_end = timeseries[idx+1]
        interval_key = interval_start.strftime("%x %X")
        interval_metrics = calculate_application_version_metrics_for_interval(version, interval_start, interval_end)
        per_version_metrics[interval_key] = interval_metrics
    return per_version_metrics


def _generate_time_series(start_date, end_date, interval, limit=None):
    time_series = list(rrule.rrule(interval, dtstart=start_date, until=end_date))
    if not limit:
        return time_series
    return time_series[-1*limit:]


def calculate_instance_metrics_for_interval(all_instances, all_histories, start_date, end_date):
    total_count = all_instances.count()
    active_count = all_instances.filter(Q(instancestatushistory__status__name='active')).distinct().count()
    # build_stats = _stats_for_instance_history(all_histories, 'build', end_date)
    # networking_stats = _stats_for_instance_history(all_histories, 'networking', end_date)
    # deploying_stats = _stats_for_instance_history(all_histories, 'deploying', end_date)
    time_specific_metrics = {
            "active": active_count,
            "total": total_count,
            # "build": build_stats,
            # "networking": networking_stats,
            # "deploying": deploying_stats,
        }
    return time_specific_metrics


def calculate_application_version_metrics_for_interval(application_version, interval_start, interval_end):
    provider_metrics = {}
    for pm in application_version.machines.all():
        all_instances = pm.instance_source.instances.all()
        all_instances = all_instances.filter(start_date__gt=interval_start, start_date__lt=interval_end)
        all_histories = InstanceStatusHistory.objects.filter(
            instance__in=all_instances)
        interval_metrics = calculate_instance_metrics_for_interval(
            all_instances, all_histories, interval_start, interval_end)
        provider_metrics[pm.instance_source.provider.location] = interval_metrics
    return provider_metrics


def get_historical_average(instance_history_list, status_name, limit=None):
    filtered_history_list = instance_history_list.filter(status__name=status_name).distinct()
    tmp_duration = ExpressionWrapper(F('end_date') - F('start_date'), output_field=fields.DurationField())
    tmp_average_time = filtered_history_list.annotate(
            tmp_duration=tmp_duration).aggregate(Avg('tmp_duration'))['tmp_duration__avg']
    return tmp_average_time


def _stats_for_instance_history(histories, status_name, end_date):
    filtered_histories = histories.filter(status__name=status_name)
    status_in_secs = map(lambda x: (x.force_end_date(end_date) - x.start_date).total_seconds(), filtered_histories)
    median_status_time = numpy.median(status_in_secs) if status_in_secs != 0 else 0
    avg_status_time = numpy.mean(status_in_secs) if status_in_secs != 0 else 0
    std_dev_status_time = numpy.std(status_in_secs) if status_in_secs != 0 else 0
    status_stats = {
        'average': avg_status_time,
        'std_deviation': std_dev_status_time,
        'median': median_status_time,
    }
    return status_stats
