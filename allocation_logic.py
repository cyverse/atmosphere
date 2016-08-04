from dateutil.parser import parse
import json
from django.db.models.query import Q
from core.models.instance_history import InstanceStatusHistory
from core.models.event_table import EventTable
from core.models.instance import Instance


def create_report(report_start_date,report_end_date):

    report_start_date = parse(report_start_date)#("2016-04-01T00:00+00:00")
    report_end_date = parse(report_end_date)#("2016-05-01T00:00+00:00")
    data = generate_data(report_start_date,report_end_date)
    write_csv(data)


def generate_data(report_start_date,report_end_date):
    #filter events and instancs
    filtered_items = filter_events_and_instances(report_start_date,report_end_date)
    #create instance to event mappings
    event_instance_dict = group_events_by_instances(filtered_items['events'])
    #get all instance status histories for the event
    filtered_instance_histories = get_all_histories_for_instance(filtered_items['instances'],report_start_date,report_end_date)
    #map events to instance status histories ids
    events_histories_dict = map_events_to_histories(filtered_instance_histories,event_instance_dict)
    #create rows of data
    data = create_rows(filtered_instance_histories,events_histories_dict,report_start_date,report_end_date)

    return data


def filter_events_and_instances(report_start_date,report_end_date):
	
    events = EventTable.objects.filter(Q(timestamp__gte=report_start_date) & Q(timestamp__lte=report_end_date))
    instances = Instance.objects.filter(
   	Q(
		Q(start_date__gte=report_start_date) & Q(start_date__lte=report_end_date)
	) | 
	Q(
		Q(end_date__gte=report_start_date) & Q(end_date__lte=report_end_date)
	) | 
	Q(
		Q(start_date__lte=report_start_date) & Q( Q(end_date__isnull=True)| Q(end_date__gte=report_end_date) )
	)
    )
	
    return {'events':events,'instances':instances}



def group_events_by_instances(events):
    out_dic = {}

    for event in events:
        out_dic.setdefault(json.loads(event.payload)['instance_id'],[]).append(event.payload)

    return out_dic

def get_all_histories_for_instance(instances,report_start_date,report_end_date):
    histories = {}
    for instance in instances:
        histories[instance.id] = instance.instancestatushistory_set.filter(
    	    ~Q(start_date__gte=report_end_date) & 
    	    ~Q( Q(end_date__isnull=False) & Q(end_date__lte=report_start_date) )
    	)

    return histories


def map_events_to_histories(filtered_instance_histories,event_instance_dict):
 
    out_dic = {}
    for instance,events in event_instance_dict.iteritems():
        hist_list = filtered_instance_histories[instance]
        for event in events:
            info = json.loads(event)
            ts = parse(info['timestamp'])
            inst_history = [i.id for i in hist_list if i.start_date <= ts and i.end_date >= ts]
            if inst_history:
                out_dic.setdefault(inst_history[-1],[]).append(info)
     
    return out_dic

def create_rows(filtered_instance_histories,events_histories_dict,report_start_date,report_end_date):
    data = []
    for instance,histories in filtered_instance_histories.iteritems():
        for hist in histories:
	    empty_row = {'username':'','instance_id':'','allocation_source':'','provider_alias':'','instance_status_history_id':'','cpu':'','memory':'',
	                'disk':'','instance_status_start_date':'','instance_status_end_date':'','report_start_date':report_start_date,'report_end_date':report_end_date,
			'instance_status':'','duration':'','applicable_duration':''}
	    filled_row = fill_data(empty_row,hist)

            if hist.id in events_histories_dict:
	        events = events_histories_dict[hist.id]
	        start_date = hist.start_date
	        for event in events:
		    end_date = parse(event['timestamp'])
					# fill out stuff
		    filled_row_temp = filled_row.copy()
		    filled_row_temp['instance_status_start_date'] = start_date
		    filled_row_temp['instance_status_end_date'] = end_date
		    filled_row_temp['allocation_source'] = event['old_allocation_source_id']
		    filled_row_temp['applicable_duration']  = calculate_allocation(hist,start_date,end_date,report_start_date,report_end_date)
		    data.append(filled_row_temp)
		    filled_row_temp = ''
		    start_date = parse(event['timestamp'])

                end_date = hist.end_date
		filled_row_temp = filled_row.copy()
		filled_row_temp['instance_status_start_date'] = start_date
		filled_row_temp['instance_status_end_date'] = end_date
		filled_row_temp['allocation_source'] = event['new_allocation_source_id']
		filled_row_temp['applicable_duration']  = calculate_allocation(hist,start_date,end_date,report_start_date,report_end_date)
		data.append(filled_row_temp)
            else:
	        filled_row['allocation_source'] = 'N/A'
		filled_row['applicable_duration']  = calculate_allocation(hist,hist.start_date,hist.end_date,report_start_date,report_end_date)
		data.append(filled_row)


    return data


def calculate_allocation(hist,start_date,end_date,report_start_date,report_end_date):

    if hist.status.name=='active':
        effective_start_date = max(start_date, report_start_date)
        effective_end_date = report_end_date if end_date is None else min(end_date, report_end_date)
        applicable_duration = (effective_end_date - effective_start_date).total_seconds()*hist.size.cpu
        return applicable_duration
    else:
        return 0


def fill_data(row,history_obj):
    row['username'] = history_obj.instance.created_by.username
    row['instance_id'] = history_obj.instance_id
    row['provider_alias'] = history_obj.instance.provider_alias
    row['instance_status_history_id'] = history_obj.id
    row['cpu'] = history_obj.size.cpu
    row['memory'] = history_obj.size.mem
    row['disk'] = history_obj.size.disk
    row['instance_status_start_date'] = history_obj.start_date
    row['instance_status_end_date'] = 'Still Running' if not history_obj.end_date else history_obj.end_date
    row['instance_status'] = history_obj.status.name
    row['duration'] = 'Still Running' if not history_obj.end_date else (history_obj.end_date - history_obj.start_date).total_seconds()
    return row

def write_csv(data):

    with open('/opt/dev/reports/new_report.csv','w+') as csv:
        csv.write("Username,Instance_ID,Allocation Source,Provider Alias,Instance_Status_History_ID,CPU,Memory,Disk,Instance_Status_Start_Date,Instance_Status_End_Date,Report_Start_Date,Report_End_Date,Instance_Status,Duration (hours),Applicable_Duration (hours)\n")

	for row in data:

	    csv.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n"%(row['username'],row['instance_id'],row['allocation_source'],
		row['provider_alias'],row['instance_status_history_id'],row['cpu'],row['memory'],row['disk'],row['instance_status_start_date'],
		row['instance_status_end_date'],row['report_start_date'],row['report_end_date'],row['instance_status'],row['duration'],row['applicable_duration']))


