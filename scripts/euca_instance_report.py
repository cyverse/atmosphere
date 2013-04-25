#!/usr/bin/env python
from atmosphere import settings
from core.models import Instance
from boto.ec2.instance import Instance as BotoInstance
from boto.ec2.regioninfo import RegionInfo
from urlparse import urlparse
from boto import connect_ec2
from dateutil import parser
from authentication.protocol.ldap import lookupUser
import subprocess
import sys, datetime, os
import smtplib, datetime
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

def _get_admin_driver():

    from core.models import Credential
    from api import getEshDriver
    identity = Credential.objects.get(value=settings.EUCA_ADMIN_SECRET).identity
    driver = getEshDriver(identity, identity.created_by)
    return driver

def _get_config_driver():

    key = settings.EUCA_ADMIN_KEY
    secret = settings.EUCA_ADMIN_SECRET
    ec2_url = settings.EUCA_EC2_URL

    parsed_url = urlparse(ec2_url)
    region = RegionInfo(None, 'eucalyptus', parsed_url.hostname)
    config = connect_ec2(aws_access_key_id=key, aws_secret_access_key=secret, 
                   is_secure=False, region=region, 
                   port=parsed_url.port, path='/services/Configuration')
    config.APIVersion = 'eucalyptus'
    return config

def _build_node_maps():
    driver = _get_config_driver()
    boto_instances = driver.get_list("DescribeNodes", {}, [('euca:item',BotoInstance)], '/')
    last_node = ''
    nodes = {}
    for inst in boto_instances:
        if hasattr(inst, 'euca:name'):
            last_node = getattr(inst, 'euca:name')
        if not hasattr(inst, 'euca:entry'):
            continue
        instance_id = getattr(inst, 'euca:entry')
        if nodes.get(last_node):
            instance_list = nodes[last_node] 
            instance_list.append(instance_id)
        else:
            nodes[last_node] = [instance_id]
    return nodes

def _test_ssh(ip_addr):
    retcode = subprocess.call(["nc","-w","10",ip_addr,"22"], stderr=open('/dev/null','w'), stdout=open('/dev/null','w'))
    return retcode == 0

def _check_instance(args):
        (node, instances, instance_id) = args
        instance = [i for i in instances if i.name == instance_id][0]
        ip_addr = instance.public_ip[0]
        ssh_status = True#_test_ssh(ip_addr)
        launch_date = parser.parse(instance.extra['launchdatetime']).utcnow()
        image_id = instance.extra['imageId']
        owner_id = instance.extra['ownerId']
        instance_info = {
            'ip':ip_addr,
            'ssh':ssh_status,
            'launch_date':launch_date,
            'image_id': image_id,
            'owner_id': owner_id,
            'instance_id':instance_id,
            'node_controller':node,
        }
        user = lookupUser(owner_id)
        if user:
            instance_info.update({
                'username':user['uid'],
                'email':user['mail'],
                'full_name': "%s %s" % (user['givenName'], user['sn'])
            })
        return instance_info

def instance_report():
    node_map = _build_node_maps()
    admin_driver = _get_admin_driver()
    instances = admin_driver._connection.list_nodes()
    report = []
    for (node,instance_list) in node_map.items():
        args_list = [(node, instances, instance_id) for instance_id in instance_list]
        node_report = map(_check_instance, args_list)
        report.append(node_report)
    return report

def csv_report():
    report = instance_report()
    csv_list = []
    for node in report:
        for instance in node:
            csv_list.append( '%s,%s,%s,%s,%s,%s,%s,%s' % (
                            instance.get('node_controller'),
                            instance.get('instance_id'),
                            instance.get('username'),
                            instance.get('full_name'),
                            instance.get('email'),
                            instance.get('image_id'),
                            instance.get('ssh'),
                            instance.get('launch_date'),
                            ))
    return csv_list

def xls_report(filename):
    import xlwt
    report = instance_report()
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('instance_report')
    #Header Row
    worksheet.write(0,0,'Node ID')
    worksheet.write(0,1,'Instance ID')
    worksheet.write(0,2,'Username')
    worksheet.write(0,3,'Full Name')
    worksheet.write(0,4,'E-Mail')
    worksheet.write(0,5,'Image ID')
    worksheet.write(0,6,'SSH Access')
    worksheet.write(0,7,'Launch Date')
    row_val = 1
    for node in report:
        #Node header Row
        for instance in node:
            worksheet.write(row_val,0,instance.get('node_controller'))
            worksheet.write(row_val,1,instance.get('instance_id'))
            worksheet.write(row_val,2,instance.get('username'))
            worksheet.write(row_val,3,instance.get('full_name'))
            worksheet.write(row_val,4,instance.get('email'))
            worksheet.write(row_val,5,instance.get('image_id'))
            worksheet.write(row_val,6,instance.get('ssh'))
            worksheet.write(row_val,7,instance.get('launch_date'))
            row_val += 1
    workbook.save(filename)
    return workbook

def send_mail(sendfrom,sendto,subject,text,files=[],server="localhost"):
    assert type(sendto)==list
    assert type(files)==list

    msg = MIMEMultipart()
    msg['From'] = sendfrom
    msg['To'] = COMMASPACE.join(sendto)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach( MIMEText(text))
    for f in files:
        part = MIMEBase('application',"octet-stream")
        part.set_payload( open(f,"rb").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)
    smtp = smtplib.SMTP(server)
    smtp.sendmail(sendfrom, sendto, msg.as_string())
    smtp.close()

def email_report(*args, **kwargs):
    email_addr = args[0]
    if type(email_addr) is not list:
        email_addr = [email_addr]
    now = datetime.datetime.now()
    xls_report('/tmp/instance_report.xls')
    send_mail('no-reply@iplantcollaborative.org', email_addr, 'Instance Report', 'Report generated on %s' % now.strftime("%Y-%m-%d at %I:%M:%S %p"), files=['/tmp/instance_report.xls'])
    os.remove('/tmp/instance_report.xls')
    return True

def usage():
    print """Eucalyptus Instance Report Generator:

Eucalyptus Instance Report Generator sends a Microsoft Excel spreadsheet with each instance, their owner and specific meta-data. 

To send an email:
  $ %s test1@email.com test2@email.com ...
""" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
        sys.exit(2)
    email_report(sys.argv[1:])
