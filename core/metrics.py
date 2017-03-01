import numpy
from django.db.models import (
        Avg, Case, Count, ExpressionWrapper,
        Func, F, Q, Sum, When,
        fields, DurationField, IntegerField)
from django.utils import timezone

from core.models import InstanceStatusHistory, Instance, AtmosphereUser


def _split_mail(email, unknown_str='unknown'):
    return email.split('@')[1].split('.')[-1:][0] if email else unknown_str


def get_image_metrics(application):
    """
    """
    all_instance_ids = application.versions.values_list('machines__instance_source__instances', flat=True).distinct()
    all_instances = Instance.objects.filter(id__in=all_instance_ids)
    all_history_ids = all_instances.values_list('instancestatushistory', flat=True).distinct()
    all_histories = InstanceStatusHistory.objects.filter(id__in=all_history_ids).order_by('-start_date')  # Latest == first
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
    # avg_networking_time = get_historical_average(all_histories, 'networking')
    # avg_deploying_time = get_historical_average(all_histories, 'deploying')
    recent_networking_time = get_historical_average(all_histories, 'networking', limit=100)
    recent_deploying_time = get_historical_average(all_histories, 'deploying', limit=100)

    return {
        'hit_active': active_count,
        'never_active': never_active_count,
        # 'average_networking': avg_networking_time,
        # 'average_deploying': avg_deploying_time,
        'recent_networking': recent_networking_time,
        'recent_deploying': recent_deploying_time,
    }


def get_historical_average(instance_history_list, status_name, limit=None):
    filtered_history_list = instance_history_list.filter(end_date__isnull=False, status__name=status_name).distinct()
    if limit:
        filtered_history_list = filtered_history_list[:limit]
    average_time = filtered_history_list.aggregate(Avg('duration'))['duration__avg']
    return average_time

def get_detailed_metrics(application, now_time=None):
    """
    Aggregate 'all-version' metrics
    More specific metrics can be found at the version level
    #FIXME: This call is *SLOW*. Once we have all the metrics we want per application, we need a way to store this (EventTable)
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
    unique_users = instances_qs.values_list('created_by__username',flat=True).distinct()
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

