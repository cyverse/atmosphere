# FIXME: Make useful per-provider-calculations, then make them fast, then include API/GUI scaffolding.
# def get_provider_metrics(interval=rrule.MONTHLY, force=False):
#     if not interval:
#         interval = rrule.MONTHLY
#     redis_cache = redis.StrictRedis()
#     key = "metrics-global-interval-%s" % (rrule.FREQNAMES[interval])
#     if redis_cache.exists(key) and not force:
#         pickled_object = redis_cache.get(key)
#         return pickle.loads(pickled_object)
#     else:
#         metrics = calculate_provider_metrics(interval)
#         pickled_object = pickle.dumps(metrics)
#         redis_cache.set(key, pickled_object)
#         redis_cache.expire(key, METRICS_CACHE_DURATION)
#     return metrics
#
# def calculate_provider_metrics(interval=rrule.MONTHLY):
#     now_time = timezone.now()
#     the_beginning = Application.objects.order_by('start_date').values_list('start_date', flat=True).first()
#     if not the_beginning:
#         the_beginning = now_time - timezone.timedelta(days=365)
#     the_end = now_time
#     timeseries = _generate_time_series(the_beginning, the_end, interval)
#     global_interval_metrics = collections.OrderedDict()
#     for idx, ts in enumerate(timeseries):
#         interval_start = ts
#         interval_key = interval_start.strftime("%x %X")
#         if idx == len(timeseries)-1:
#             interval_end = the_end
#         else:
#             interval_end = timeseries[idx+1]
#         provider_metrics = {}
#         for prov in Provider.objects.filter(only_current(), active=True):
#             provider_metrics[prov.location] = calculate_metrics_per_provider(prov, interval_start, interval_end)
#         global_interval_metrics[interval_key] = provider_metrics
#     return global_interval_metrics
#
#
# def calculate_metrics_per_provider(provider, interval_start, interval_end):
#     all_instance_ids = provider.instancesource_set.filter(
#         instances__start_date__gt=interval_start,
#         instances__start_date__lt=interval_end)\
#                 .values_list('instances', flat=True)
#     all_histories = InstanceStatusHistory.objects.filter(
#         instance__id__in=all_instance_ids)
#     all_instances = Instance.objects.filter(
#         id__in=all_instance_ids)
#     provider_interval_metrics = calculate_instance_metrics_for_interval(
#         all_instances, all_histories, interval_start, interval_end)
#     provider_user_metrics = calculate_provider_user_metrics(all_instances)
#     provider_metrics = provider_interval_metrics.update(provider_user_metrics)
#     return provider_metrics
#
#
# def calculate_provider_user_metrics(instances_qs):
#     # user_domains = _get_user_domain_map(instances_qs)
#     # unique_users = _get_unique_users(instances_qs)
#     instance_stats = _get_instance_percentages(instances_qs)
#     return {
#         # 'domains': user_domains,
#         # 'count': unique_users.count(),
#         'statistics': instance_stats
#     }
#
#
# def _get_user_domain_map(instances_qs):
#     user_domain_map = {}
#     unique_users = _get_unique_users(instances_qs)
#     for username in unique_users:
#         user = AtmosphereUser.objects.get(username=username)
#         email_str = _split_mail(user.email)
#         user_count = user_domain_map.get(email_str, 0)
#         user_count += 1
#         user_domain_map[email_str] = user_count
#     return user_domain_map
#
#
# def _get_unique_users(instances_qs):
#     unique_users = instances_qs.values_list('created_by__username', flat=True).distinct()
#     return unique_users
#
#
# def _split_mail(email, unknown_str='unknown'):
#     return email.split('@')[1].split('.')[-1:][0] if email else unknown_str
#
# def _get_instance_percentages(instances_qs):
#     count = instances_qs.count()
#     total_hours = 0
#     last_active = 0
#     last_inactive = 0
#     last_error = 0
#     for instance in instances_qs.all():
#         total_hours += instance.get_total_hours()
#         last_history = instance.get_last_history()
#         if not last_history:
#             pass
#         elif instance.has_history('active'):
#             last_active += 1
#         elif last_history.status.name == 'deploy_error':
#             last_error += 1
#         else:
#             last_inactive += 1
# 
#     if count:
#         error_pct = last_error / float(count) * 100
#         active_pct = last_active / float(count) * 100
#         inactive_pct = last_inactive / float(count) * 100
#         avg_time_used = total_hours / float(count)
#     else:
#         error_pct = 0
#         active_pct = 0
#         inactive_pct = 0
#         avg_time_used = 0
#     return {
#         'active': active_pct,
#         'inactive': inactive_pct,
#         'error': error_pct,
#         'instances_launched': count,
#         'instances_total_hours': total_hours,
#         'instances_total_hours_avg': avg_time_used,
#     }
#
#
