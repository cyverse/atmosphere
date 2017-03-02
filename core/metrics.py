import pickle
import collections
import numpy
import redis

from django.db.models import (
        Avg, Case, ExpressionWrapper,
        F, Q, Sum, When,
        fields, IntegerField)
from django.utils import timezone
from dateutil import rrule
from core.models import Application, Provider, InstanceStatusHistory, Instance, AtmosphereUser
from core.query import only_current


METRICS_CACHE_DURATION = 60*60  # One hour


def _split_mail(email, unknown_str='unknown'):
    return email.split('@')[1].split('.')[-1:][0] if email else unknown_str


def get_image_metrics(application, interval=rrule.MONTHLY):
    """
    Skip image metrics on end-dated applications
    Otherwise look through the cache to find application metrics
    """
    metrics = {}
    if application.end_date:
        return metrics
    metrics = _image_interval_metrics(application, interval),
    return metrics


def _image_interval_metrics(application, interval=rrule.MONTHLY):
    if not interval:
        interval = rrule.MONTHLY
    redis_cache = redis.StrictRedis()
    key = "metrics-application-%s-interval-%s" % (application.id, rrule.FREQNAMES[interval])
    if redis_cache.exists(key):
        pickled_object = redis_cache.get(key)
        return pickle.loads(pickled_object)
    else:
        metrics = _calculate_image_interval_metrics(application, interval)
        pickled_object = pickle.dumps(metrics)
        redis_cache.set(key, pickled_object)
        redis_cache.expire(key, METRICS_CACHE_DURATION)
    return metrics


def _calculate_image_interval_metrics(application, interval=rrule.MONTHLY):
    """
    From start_date of Application to now/End-date of application
      - Create a timeseries by splitting by 'interval'
      - Query for metrics datapoints
      - Return the timeseries + datapoints
    """
    now_time = timezone.now()
    the_beginning = application.start_date
    the_end = application.end_date or now_time
    timeseries = list(rrule.rrule(interval, dtstart=the_beginning, until=the_end))
    application_metrics = {}
    for version in application.versions.all():
        version_metrics = collections.OrderedDict()
        for idx, ts in enumerate(timeseries):
            interval_start = ts
            if idx == len(timeseries)-1:
                interval_end = the_end
            else:
                interval_end = timeseries[idx+1]
            interval_key = interval_start.strftime("%X %x")
            interval_metrics = _get_interval_metrics_by_version(version, interval_start, interval_end)
            version_metrics[interval_key] = interval_metrics
        application_metrics[version.name] = version_metrics
    return application_metrics


def _average_interval_metrics(interval=rrule.MONTHLY):
    if not interval:
        interval = rrule.MONTHLY
    redis_cache = redis.StrictRedis()
    key = "metrics-global-interval-%s" % (rrule.FREQNAMES[interval])
    if redis_cache.exists(key):
        pickled_object = redis_cache.get(key)
        return pickle.loads(pickled_object)
    else:
        metrics = _calculate_average_interval_metrics(interval)
        pickled_object = pickle.dumps(metrics)
        redis_cache.set(key, pickled_object)
        redis_cache.expire(key, METRICS_CACHE_DURATION)
    return metrics


def _calculate_average_interval_metrics(interval=rrule.MONTHLY):
    now_time = timezone.now()
    the_beginning = Application.objects.order_by('start_date').values_list('start_date', flat=True).first()
    if not the_beginning:
        the_beginning = now_time - timezone.timedelta(days=365)
    the_end = now_time
    timeseries = list(rrule.rrule(interval, dtstart=the_beginning, until=the_end))
    global_interval_metrics = collections.OrderedDict()
    for idx, ts in enumerate(timeseries):
        interval_start = ts
        interval_key = interval_start.strftime("%X %x")
        if idx == len(timeseries)-1:
            interval_end = the_end
        else:
            interval_end = timeseries[idx+1]
        provider_metrics = {}
        for prov in Provider.objects.filter(only_current(), active=True):
            all_instance_ids = prov.instancesource_set.filter(
                instances__start_date__gt=interval_start,
                instances__start_date__lt=interval_end)\
                        .values_list('instances', flat=True)
            all_instances = Instance.objects.filter(id__in=all_instance_ids)
            provider_interval_metrics = _get_instance_metrics(all_instances, interval_start, interval_end)
            provider_metrics[prov.location] = provider_interval_metrics
        global_interval_metrics[interval_key] = provider_metrics
    return global_interval_metrics

## OLD below this line:
def _get_interval_metrics_by_version(application_version, interval_start, interval_end):
    provider_metrics = {}
    for pm in application_version.machines.all():
        all_instances = pm.instance_source.instances.all()
        all_instances = all_instances.filter(start_date__gt=interval_start, start_date__lt=interval_end)
        interval_metrics = _get_instance_metrics(all_instances, interval_start, interval_end)
        provider_metrics[pm.instance_source.provider.location] = interval_metrics
    return provider_metrics


def _get_instance_metrics(all_instances, start_date, end_date):
    total_count = all_instances.count()
    active_count = all_instances.filter(Q(instancestatushistory__status__name='active')).distinct().count()
    time_specific_metrics = {
            "active": active_count,
            "total": total_count
        }
    return time_specific_metrics


def _image_count_metrics(all_instances):
    # Method 1 Conditional Aggregation - Faster!
    annotated_qs = all_instances.annotate(num_active=Sum(
        Case(
            When(instancestatushistory__status__name='active', then=1),
            default=0,
            output_field=IntegerField()
        )
    ))
    active_count = annotated_qs.filter(num_active__gt=0).distinct().count()
    never_active_count = annotated_qs.filter(num_active=0).distinct().count()
    # Method 2 - easier to read!
    # active_count = all_instances.filter( Q(instancestatushistory__status__name='active')).distinct().count()
    # never_active_count = all_instances.filter( ~Q(instancestatushistory__status__name='active')).distinct().count()
    metrics = {'active_count': active_count, 'never_active_count': never_active_count}
    return metrics


def _image_average_metrics(all_histories):
    # avg_networking_time = get_historical_average(all_histories, 'networking')
    # avg_deploying_time = get_historical_average(all_histories, 'deploying')
    recent_networking_time = get_historical_average(all_histories, 'networking', limit=100)
    recent_deploying_time = get_historical_average(all_histories, 'deploying', limit=100)

    return {
        # 'average_networking': avg_networking_time,
        # 'average_deploying': avg_deploying_time,
        'recent_networking': recent_networking_time,
        'recent_deploying': recent_deploying_time,
    }


def get_historical_average(instance_history_list, status_name, limit=None):
    filtered_history_list = instance_history_list.filter(end_date__isnull=False, status__name=status_name).distinct()
    if limit:
        filtered_history_list = filtered_history_list[:limit]
    # METHOD 1: using the 'tmp_duration' annotation
    tmp_duration = ExpressionWrapper(F('end_date') - F('start_date'), output_field=fields.DurationField())
    tmp_average_time = filtered_history_list.annotate(
            tmp_duration=tmp_duration).aggregate(Avg('tmp_duration'))['tmp_duration__avg']
    return tmp_average_time
    # METHOD 2: using the 'duration' column
    # average_time = filtered_history_list.aggregate(Avg('duration'))['duration__avg']
    # return average_time


def get_detailed_metrics(application, now_time=None):
    """
    Aggregate 'all-version' metrics
    More specific metrics can be found at the version level
    #FIXME: This call is *SLOW*. Once we have all the metrics we want per application,
    we need a way to store this (EventTable)
    """
    if not now_time:
        now_time = timezone.now()
    versions = application.versions.all()
    version_map = {}
    for version in versions:
        version_metrics = get_version_metrics(version, now_time)
        version_map[version.name] = version_metrics
    return {'versions': version_map}


def get_version_metrics(version, now_time=None):
    """
    # TODO: Consider how this question could be answered
    # with 'allocation' and the engine/routines used inside it..
    """
    if not now_time:
        now_time = timezone.now()
    instances_qs = Instance.objects.filter(source__providermachine__application_version=version)
    user_domain_map = {}
    instance_ids = instances_qs.values_list('id', flat=True)
    histories = InstanceStatusHistory.objects.filter(instance__id__in=instance_ids)
    networking = histories.filter(status__name='networking')
    networking_in_secs = map(lambda x: (x.force_end_date(now_time) - x.start_date).total_seconds(), networking)
    median_networking = numpy.median(networking_in_secs)
    avg_networking = numpy.mean(networking_in_secs)
    std_dev_networking = numpy.std(networking_in_secs)
    networking_stats = {
        'average': avg_networking,
        'std_deviation': std_dev_networking,
        'median': median_networking,
    }
    deploying = histories.filter(status__name='deploying')
    deploying_in_secs = map(lambda x: (x.force_end_date(now_time) - x.start_date).total_seconds(), deploying)
    median_deploying = numpy.median(deploying_in_secs)
    avg_deploying = numpy.mean(deploying_in_secs)
    std_dev_deploying = numpy.std(deploying_in_secs)
    deploying_stats = {
        'average': avg_deploying,
        'std_deviation': std_dev_deploying,
        'median': median_deploying,
    }
    count = instances_qs.count()
    unique_users = instances_qs.values_list('created_by__username', flat=True).distinct()
    for username in unique_users:
        user = AtmosphereUser.objects.get(username=username)
        email_str = _split_mail(user.email)
        user_count = user_domain_map.get(email_str, 0)
        user_count += 1
        user_domain_map[email_str] = user_count
    total_hours = 0
    last_active = 0
    last_inactive = 0
    last_error = 0
    for instance in instances_qs.all():
        total_hours += instance.get_total_hours()
        last_history = instance.get_last_history()
        if not last_history:
            pass
        elif instance.has_history('active'):
            last_active += 1
        elif last_history.status.name == 'deploy_error':
            last_error += 1
        else:
            last_inactive += 1

    if count:
        error_pct = last_error / float(count) * 100
        active_pct = last_active / float(count) * 100
        inactive_pct = last_inactive / float(count) * 100
        avg_time_used = total_hours / float(count)
    else:
        error_pct = 0
        active_pct = 0
        inactive_pct = 0
        avg_time_used = 0

    user_stats = {
        'total': unique_users.count(),
        'domains': user_domain_map,
    }
    metrics = {
        'instances_launched': count,
        'instances_total_hours': total_hours,
        'instances_total_hours_avg': avg_time_used,
        'status_in_secs': {
            'networking': networking_stats,
            'deploying': deploying_stats,
        },
        'status_in_percents': {
            'active': active_pct,
            'inactive': inactive_pct,
            'error': error_pct,
        },
        'users': user_stats,
    }
    return metrics
