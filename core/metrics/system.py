from django.utils import timezone
from django.db.models import Q
from dateutil import rrule
from core.models import (
    InstanceStatusHistory, Instance, AtmosphereUser, MachineRequest,
    Application, ProviderMachine, Provider
)


def instance_history_usage_report(filename, start_date=None, end_date=None, only_active=False):
    query = InstanceStatusHistory.objects.all()
    if only_active:
        query = query.filter(Q(status__name='active') | Q(status__name='running'))
    if start_date:
        query = query.filter(start_date__gt=start_date)
    if end_date:
        query = query.filter(end_date__gt=end_date)
    with open(filename, 'w') as the_file:
        the_file.write("ID,Provider Alias,Username,Provider,Application,Version,Machine UUID,Status,Start Date,End Date,Active Time(Hours),CPU,RAM,DISK\n")
        for instance_history in query.order_by('instance__id', 'start_date', 'end_date'):
            instance = instance_history.instance
            size = instance_history.size
            cpu = size.cpu if size.cpu > 0 else 1
            mem = size.mem if size.mem > 1 else ""
            disk = size.disk if size.disk > 1 else ""
            machine = instance.source.providermachine
            active_time = instance_history.get_active_time()[0]

            the_file.write(
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" %
                (instance.id, instance.provider_alias,
                 instance.created_by.username,
                 instance.created_by_identity.provider.location,
                 machine.application.name.replace(",", ""),
                 machine.application_version.name.replace(",", ""),
                 instance.source.identifier, instance_history.status.name,
                 instance_history.start_date.strftime("%x %X"),
                 instance_history.end_date.strftime("%x %X")
                 if instance_history.end_date else "N/A",
                 active_time.total_seconds() / 3600.0, cpu, mem, disk))


def instance_usage_report(filename, start_date=None, end_date=None):
    query = Instance.objects.all()
    if start_date:
        query = query.filter(start_date__gt=start_date)
    if end_date:
        query = query.filter(end_date__gt=end_date)
    now_time = timezone.now()
    with open(filename, 'w') as the_file:
        the_file.write("ID,Provider Alias,Username,Provider,Application,Version,Machine UUID,Start Date,End Date,Active Time(Hours),CPU,RAM,DISK\n")
        for instance in query.order_by('start_date', 'end_date'):
            size = instance.get_size()
            cpu = size.cpu if size.cpu > 0 else 1
            mem = size.mem if size.mem > 1 else ""
            disk = size.disk if size.disk > 1 else ""
            machine = instance.source.providermachine
            active_time = instance.get_active_time()[0]

            the_file.write( "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                instance.id, instance.provider_alias, instance.created_by.username,
                instance.created_by_identity.provider.location, machine.application.name.replace(",",""), machine.application_version.name.replace(",",""),
                instance.source.identifier, instance.start_date.strftime("%x %X"), instance.end_date.strftime("%x %X") if instance.end_date else now_time.strftime("%x %X"),
                active_time.total_seconds()/3600.0,
                cpu, mem, disk
                ) )


def machine_request_report(filename, start_date=None, end_date=None):
    query = MachineRequest.objects.filter(old_status='completed')
    if start_date:
        query = query.filter(start_date__gt=start_date)
    if end_date:
        query = query.filter(end_date__gt=end_date)
    with open(filename, 'w') as the_file:
        the_file.write("ID,Username,Provider,Application,Version,Start Date,Created on,Visibility\n")
        for mr in query.order_by('start_date', 'end_date'):
            the_file.write( "%s,%s,%s,%s,%s,%s,%s,%s\n" % (mr.id, mr.created_by.username, mr.new_machine_provider.location, mr.new_machine.application.name if mr.new_machine else "N/A", mr.new_machine.application_version.name if mr.new_machine else "N/A", mr.start_date.strftime("%x %X"), mr.end_date.strftime("%x %X") if mr.end_date else "N/A", "public" if mr.new_application_visibility == "public" else "private") )

def monthly_metrics(filename, start_date, end_date):
    monthly_breakdown = list(rrule.rrule(dtstart=start_date, freq=rrule.MONTHLY, until=timezone.now()))
    with open(filename, 'w') as the_file:
        the_file.write("Start Date,End Date,Instances launched,Users Joined,Applications Created,Machines Added\n")
        for idx, month in enumerate(monthly_breakdown):
            if idx == len(monthly_breakdown) - 1:
                continue
            start_date = month
            end_date = monthly_breakdown[idx+1]
            provider_ids = Provider.objects.filter(active=True, end_date__isnull=True).values_list("id", flat=True)
            the_file.write(_print_csv_row_between_dates(provider_ids, start_date, end_date))
            the_file.write("\n")
    return the_file


def _print_csv_row_between_dates(provider_ids, start_date, end_date, pretty_print=False):
    instances = Instance.objects.filter(start_date__gt=start_date, start_date__lt=end_date)
    users = AtmosphereUser.objects.filter(date_joined__gt=start_date, date_joined__lt=end_date)
    apps = Application.objects\
        .filter(start_date__gt=start_date, start_date__lt=end_date)\
        .filter(created_by_identity__provider__id__in=provider_ids).distinct()
    machines = ProviderMachine.objects\
        .filter(instance_source__start_date__gt=start_date, instance_source__start_date__lt=end_date)\
        .filter(instance_source__provider__id__in=provider_ids).distinct()
    if pretty_print:
        return """Between %s and %s:
            %s Instances launched
            %s Users joined
            %s Applications (%s Machines) created""" % (
                start_date, end_date,
                instances.count(), users.count(), apps.count(), machines.count())
    return "%s,%s,%s,%s,%s,%s" % (
            start_date.strftime("%x %X"), end_date.strftime("%x %X"),
            instances.count(), users.count(), apps.count(), machines.count())
