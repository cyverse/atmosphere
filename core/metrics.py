import numpy
from django.db.models import F, ExpressionWrapper, fields
from django.utils import timezone

from core.models import InstanceStatusHistory, Instance, AtmosphereUser


def _split_mail(email, unknown_str='unknown'):
    return email.split('@')[1].split('.')[-1:][0] if email else unknown_str


def get_metrics(application, now_time=None):
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

