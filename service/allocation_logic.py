from dateutil.parser import parse
import pytz
import datetime
from django.db.models.query import Q
from core.models.event_table import EventTable
from core.models.instance import Instance
from core.models.allocation_source import UserAllocationSource, AllocationSource


def create_report(report_start_date, report_end_date, user_id=None, allocation_source_name=None):
    if not report_start_date or not report_end_date:
        raise Exception("Start date and end date missing for allocation calculation function")
    try:
        report_start_date = report_start_date if isinstance(report_start_date, datetime.datetime) else parse(report_start_date)
        report_end_date = report_end_date if isinstance(report_end_date, datetime.datetime) else parse(report_end_date)
    except:
        raise Exception("Cannot parse start and end dates for allocation calculation function")
    data = generate_data(report_start_date, report_end_date, username=user_id)

    if allocation_source_name:
        output = []
        for row in data:
            if row['allocation_source'] == allocation_source_name:
                output.append(row)
        return output

    return data

def generate_data(report_start_date, report_end_date, username=None):
    # filter events and instancs)
    filtered_items = filter_events_and_instances(report_start_date, report_end_date, username=username)
    # create instance to event mappings
    event_instance_dict = group_events_by_instances(filtered_items['events'])
    # get all instance status histories for the event
    filtered_instance_histories = get_all_histories_for_instance(filtered_items['instances'], report_start_date, report_end_date)
    # map events to instance status histories ids
    events_histories_dict = map_events_to_histories(filtered_instance_histories, event_instance_dict)
    # create rows of data
    data = create_rows(filtered_instance_histories, events_histories_dict, report_start_date, report_end_date)
    return data


def filter_events_and_instances(report_start_date, report_end_date, username=None):
    events = EventTable.objects.filter(Q(timestamp__gte=report_start_date) & Q(timestamp__lte=report_end_date) & Q(name__exact="instance_allocation_source_changed")).order_by('timestamp')
    instances = Instance.objects.filter(
        Q(
            Q(start_date__gte=report_start_date) & Q(start_date__lte=report_end_date)
        ) |
        Q(
            Q(end_date__gte=report_start_date) & Q(end_date__lte=report_end_date)
        ) |
        Q(
            Q(start_date__lte=report_start_date) & Q(Q(end_date__isnull=True) | Q(end_date__gte=report_end_date))
        )
    )
    if username:
        from core.models.user import AtmosphereUser
        try:
            user_id_int = AtmosphereUser.objects.get(username=username)
        except:
            raise Exception("User '%s' does not exist"%(username))
        events = events.filter(Q(payload__username__exact=username) | Q(entity_id=username)).order_by('timestamp')
        instances = instances.filter(Q(created_by__exact=user_id_int))
    return {'events': events, 'instances': instances}


def group_events_by_instances(events):
    out_dic = {}

    for event in events:
        out_dic.setdefault(event.payload['instance_id'], []).append(event)

    return out_dic


def get_all_histories_for_instance(instances, report_start_date, report_end_date):
    histories = {}
    for instance in instances:
        histories[instance.provider_alias] = instance.instancestatushistory_set.filter(
                ~Q(start_date__gte=report_end_date) & 
                ~Q(
                    Q(end_date__isnull=False) & Q(end_date__lte=report_start_date)
                  )
            ).order_by('start_date')

    return histories


def map_events_to_histories(filtered_instance_histories, event_instance_dict):
    out_dic = {}
    for instance, events in event_instance_dict.iteritems():
        hist_list = filtered_instance_histories.get(instance,[])
        for info in events:
            ts = info.timestamp
            inst_history = [i.id for i in hist_list if i.start_date <= ts and ((not i.end_date) or (i.end_date and i.end_date >= ts))]
            if inst_history:
                out_dic.setdefault(inst_history[-1], []).append(info)
    return out_dic

def get_allocation_source_name_from_event(username, report_start_date, instance_id):
    events = EventTable.objects.filter(Q(timestamp__lt=report_start_date) & Q(name__exact="instance_allocation_source_changed") & Q(Q(payload__username__exact=username) | Q(entity_id=username)) & Q(payload__instance_id__exact=instance_id)).order_by('timestamp')
    if not events:
        return False
    else:
        allocation_source_object = AllocationSource.objects.filter(source_id=events.last().payload['allocation_source_id'])
        if allocation_source_object:
            return allocation_source_object.last().name
        else:
            raise Exception('Allocation Source ID %s in event %s does not exist' % (events.last().payload['allocation_source_id'],events.last().id))
       

def create_rows(filtered_instance_histories, events_histories_dict, report_start_date, report_end_date):
    data = []
    current_user = ''
    allocation_source_name = ''
    current_instance_id = ''
    burn_rate_per_user = {}

    still_running = _get_current_date_utc()
    total_burn_rate = 0
    for instance, histories in filtered_instance_histories.iteritems():
        for hist in histories:
            if current_user != hist.instance.created_by.username:
                if current_user:
                    burn_rate_per_user[current_user] = burn_rate_per_user.get(current_user, 0) + total_burn_rate
                current_user = hist.instance.created_by.username

            if current_instance_id != hist.instance.id:
                current_as_name = get_allocation_source_name_from_event(current_user,report_start_date,hist.instance.provider_alias)
                allocation_source_name = current_as_name if current_as_name else 'N/A' 
                current_instance_id = hist.instance.id
            
            empty_row = {'username': '', 'instance_id': '', 'allocation_source': '', 'provider_alias': '', 'instance_status_history_id': '', 'cpu': '', 'memory': '',
                         'disk': '', 'instance_status_start_date': '', 'instance_status_end_date': '', 'report_start_date': report_start_date, 'report_end_date': report_end_date,
                         'instance_status': '', 'duration': '', 'applicable_duration': '', 'burn_rate': ''}
            filled_row = fill_data(empty_row, hist, allocation_source_name)
            # check if instance is active and has no end date. If so, increment total burn rate
            if hist.status.name == 'active' and not hist.end_date:
                total_burn_rate += 1
            filled_row['burn_rate'] = total_burn_rate
            if hist.id in events_histories_dict:
                events = events_histories_dict[hist.id]
                start_date = hist.start_date
                for event in events:
                    end_date = event.timestamp
                    # fill out stuff
                    filled_row_temp = filled_row.copy()
                    filled_row_temp['instance_status_start_date'] = start_date
                    filled_row_temp['instance_status_end_date'] = end_date
                    filled_row_temp['allocation_source'] = allocation_source_name 
                    try:
                        new_allocation_source = AllocationSource.objects.get(source_id=event.payload['allocation_source_id']).name
                    except:
                        new_allocation_source = 'N/A'
                    allocation_source_name = new_allocation_source
                    filled_row_temp['applicable_duration'] = calculate_allocation(hist, start_date, end_date, report_start_date, report_end_date)
                    data.append(filled_row_temp)
                    filled_row_temp = ''
                    start_date = event.timestamp
                end_date = still_running if not hist.end_date else hist.end_date
                filled_row_temp = filled_row.copy()
                filled_row_temp['instance_status_start_date'] = start_date
                filled_row_temp['instance_status_end_date'] = end_date
                filled_row_temp['allocation_source'] = allocation_source_name
                filled_row_temp['applicable_duration'] = calculate_allocation(hist, start_date, end_date, report_start_date, report_end_date)
                data.append(filled_row_temp)
            else:
                end_date = still_running if not hist.end_date else hist.end_date
                filled_row['applicable_duration'] = calculate_allocation(hist, hist.start_date, end_date, report_start_date, report_end_date)
                data.append(filled_row)

    return data


def calculate_allocation(hist, start_date, end_date, report_start_date, report_end_date):

    if hist.status.name == 'active':
        effective_start_date = max(start_date, report_start_date)
        effective_end_date = report_end_date if end_date is None else min(end_date, report_end_date)
        applicable_duration = (effective_end_date - effective_start_date).total_seconds()*hist.size.cpu
        return applicable_duration
    else:
        return 0


def _get_current_date_utc():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def fill_data(row, history_obj, allocation_source):
    still_running = _get_current_date_utc()
    row['username'] = history_obj.instance.created_by.username
    row['allocation_source'] = allocation_source
    row['instance_id'] = history_obj.instance_id
    row['provider_alias'] = history_obj.instance.provider_alias
    row['instance_status_history_id'] = history_obj.id
    row['cpu'] = history_obj.size.cpu
    row['memory'] = history_obj.size.mem
    row['disk'] = history_obj.size.disk
    row['instance_status_start_date'] = history_obj.start_date
    row['instance_status_end_date'] = still_running if not history_obj.end_date else history_obj.end_date
    row['instance_status'] = history_obj.status.name
    row['duration'] = (still_running - history_obj.start_date).total_seconds() if not history_obj.end_date else (history_obj.end_date - history_obj.start_date).total_seconds()
    return row


def write_csv(data):

    with open('/opt/dev/reports/new_report.csv', 'w+') as csv:
        csv.write("Username,Instance_ID,Allocation Source,Provider Alias,Instance_Status_History_ID,CPU,Memory,Disk,Instance_Status_Start_Date,Instance_Status_End_Date,Report_Start_Date,Report_End_Date,Instance_Status,Duration (hours),Applicable_Duration (hours)\n")

        for row in data:

            csv.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                row['username'], row['instance_id'], row['allocation_source'],
                row['provider_alias'], row['instance_status_history_id'],
                row['cpu'], row['memory'], row['disk'],
                row['instance_status_start_date'],
                row['instance_status_end_date'],
                row['report_start_date'],
                row['report_end_date'],
                row['instance_status'],
                row['duration'], row['applicable_duration']))


def get_instance_burn_rate_from_row(row):
    burn_rate = 0
    is_active = row['instance_status'] == 'active'
    if is_active:
        no_end_date = not row['instance_status_end_date']
        ends_after_report_end = row['instance_status_end_date'] >= row['report_end_date']
        starts_before_report_end = row['instance_status_start_date'] < row['report_end_date']
        is_running_at_report_end = no_end_date or (starts_before_report_end and ends_after_report_end)
        if is_running_at_report_end:
            burn_rate = row['cpu']
    return burn_rate
