from core.models import Instance
from django.utils import timezone
import django
django.setup()


def top_launches(count, instance_set):
    identity_set = instance_set.values('created_by_identity').distinct()
    top_list = []
    for ident in identity_set:
        if is_staff(ident):
            continue
        ident_instances = instance_set.filter(created_by_identity=ident)
        instance_count = len(ident_instances)
        check_top_list(top_list, ident, instance_count, count)


def check_top_list(top_list, key, value, max_count):
    if len(top_list) < max_count:


def top_total_time(count, instance_set):


def total_launch_count(instance_set):


def main():
    now_time = timezone.now()
    prev_time = now_time - timezone.timedelta(days=365)
    instance_set = Instance.objects.filter(
        start_date__range=[
            prev_time,
            now_time])
    top_launches(20, instance_set)
    top_total_time(20, instance_set)
    total_launch_count(instance_set)
