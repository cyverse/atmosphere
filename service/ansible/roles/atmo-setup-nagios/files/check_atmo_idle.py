#!/usr/bin/env python
# Author: Andre Mercer
# Last Edited By: Chris LaRose
# 2012-02-22
import time
import sys
import os
import subprocess
import datetime
import ldap
from optparse import OptionParser
from httplib2 import Http
try: import json
except ImportError: import simplejson as json

class CheckAtmoIdlePlugin:
	def __init__(self, thresholds=None):
		self.commands = {
			"grep":		"/bin/grep",
			"lastlog":	"/usr/bin/lastlog",
			"ps":		"/bin/ps aux",
			"su":		"/bin/su",
			"xprintidle":	"/usr/local/bin/xprintidle",
			"awk":		"awk",
			"cat":		"/bin/cat"
		}
		self.tmp_file_path = "/tmp/vncData.txt"
		if thresholds is not None:
			self.thresholds = thresholds
		else:
			self.thresholds = {'warning': 30, 'critical': 30}


	def get_staff_users(self):
		"""
		Return a set of usernames of the LDAP group 'core-services'
		"""
                server = "ldap://ldap.iplantcollaborative.org"
                l = ldap.initialize(server)
                results = l.search_s('ou=Groups,dc=iplantcollaborative,dc=org', ldap.SCOPE_SUBTREE, '(cn=core-services)')
                (dn, entry) = results[0]
                return set(entry['memberUid'])

	def get_owner(self):
		"""
		Return the username of the owner of this box
		"""
		h = Http()
		resp, content = h.request("http://dedalus.iplantc.org/instances/whoami", headers={'cache-control': 'no-cache'})
		if resp['status'] != "200":
			return None
		else:
			instance = json.loads(content)	
			return instance['user']['username']	

	def last_ssh(self):
		"""
		Return the most recent login time of a user who used the machine though a pseudo terminal slave,
		excluding core services users as well as root login. 
		"""
		excluded_users = self.get_staff_users()
		excluded_users.discard(self.user)
		excluded_users.add('root')

		lastlog = subprocess.Popen(self.commands['lastlog'], stdout=subprocess.PIPE)
		grep = subprocess.Popen([self.commands['grep'], 'pts/[0-9][0-9]*'], stdout=subprocess.PIPE, stdin=lastlog.stdout)
		logins = {} # a (username: login time) dict
		for line in grep.stdout:
			line_data = line.split()
			user = line_data[0]
			if user not in excluded_users:
				login_time = self.parse_time(" ".join(line_data[4:9]))
				logins[user] = login_time
		login_times = [v for (k,v) in logins.iteritems()]
		if len(login_times) == 0:
			return None
		else:
			return max(login_times)

	def parse_time(self, time_str):
		"""
		Given a string of the form "Dec 10 21:40:04 -0700 2012" return a utc datetime object
		"""
		time_data = time_str.split()
		login_time = time.strptime(" ".join([time_data[0], time_data[1], time_data[2], time_data[4]]), "%b %d %H:%M:%S %Y")
		last_login_local = datetime.datetime(*login_time[0:6])

		offset_string = time_data[3]
		offset_sign = offset_string[0]
		offset_hours = int(offset_string[1:3])
		offset_minutes = int(offset_string[3:5])
		offset_seconds = (offset_hours * 60 * 60) + (offset_minutes * 60)
		if offset_sign == "-":
			offset_seconds = offset_seconds * -1

		last_login_utc = last_login_local - datetime.timedelta(seconds=offset_seconds)

		return last_login_utc

	def last_vnc(self):
		"""
		Return the last vnc time as a datetime obj from reading from a temporary data
		file. If the file doesn't exist, return None
		"""

		if os.path.exists(self.tmp_file_path):
			file_read_cmd = "%s %s" % (self.commands['cat'], self.tmp_file_path)
			file_read = subprocess.Popen(file_read_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

			file_read_output = file_read.stdout.read().strip()
			if len(file_read_output) > 0:
				vnc_data = [(int(y[0]), int(y[1])) for y in [x.split('\t') for x in file_read_output.split('\n')]]
				last_vnc_times = [x[0]*1000 - x[1] for x in vnc_data]
				#print last_vnc_times
				
				last_vnc_time = max(last_vnc_times)

				last_vnc_time_seconds = last_vnc_time / 1000
				last_vnc = datetime.datetime.utcfromtimestamp(last_vnc_time_seconds)
				return last_vnc
			else:
				return None
		else:
			return None

	def write_vnc_data(self):
		"""
		Write VNC session data to a temporary file
		"""
		if os.path.exists(self.tmp_file_path):
			os.remove(self.tmp_file_path)

		vncSearch = subprocess.Popen(self.commands['ps'] +" | "+ self.commands['grep'] + "  vnc | " + self.commands['grep'] + " Xvnc | "+ self.commands['grep'] + " -v grep |" + self.commands['grep'] + " -v /etc | " + self.commands['awk'] + " '{ print $12, $14 }'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		# an array of 2-tuples, which each tuple being of the form (display, user)
		vnc_sessions = []
		for line in vncSearch.stdout.readlines():
			line_arr = line.split()
			vnc_sessions.append((line_arr[0], line_arr[1].split('/')[2]))

		for session in vnc_sessions:
			idle_append_cmd = '%s %s -c "env DISPLAY=%s %s" >> %s &' % (self.commands['su'], session[1], session[0], self.commands['xprintidle'], self.tmp_file_path)
			idleSearch = subprocess.Popen( idle_append_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		return True
	

	class nagios_data:

		status_strings = ['OK', "WARNING", "CRITICAL", "UNKNOWN"]
		content = ""
		perfdata = None
		status = 3

		def exit(self):
			if self.perfdata is None:
				print "%s: %s" % (self.status_strings[self.status], self.content)
			else:
				print "%s: %s | %s" % (self.status_strings[self.status], self.content, perfdata_dict_to_str(self.perfdata))
			sys.exit(self.status)


	def run(self):
		self.user = self.get_owner()
		out = self.nagios_data()
		if self.user is None:
			out.content = "Username could not be reliably determined"
			out.status = 3
			out.exit()
		else:
			last_ssh = self.last_ssh()
			last_vnc = self.last_vnc()
		
			self.write_vnc_data()

			now = datetime.datetime.utcnow()

			out.perfdata = {}
			if last_ssh is not None:
				out.perfdata['ssh'] = ((now-last_ssh).days, self.thresholds['warning'], self.thresholds['critical'])
			else:
				out.perfdata['ssh'] = (-1, self.thresholds['warning'], self.thresholds['critical'])

			if last_vnc is not None:
				out.perfdata['vnc'] = ((now-last_vnc).days, self.thresholds['warning'], self.thresholds['critical'])
			else:
				out.perfdata['vnc'] = (-1, self.thresholds['warning'], self.thresholds['critical'])

			if last_ssh is not None or last_vnc is not None:
				last_activity = max(i for i in [last_ssh, last_vnc] if i is not None)
				last_activity_delta = now - last_activity

				out.content = "Last activity was %d days ago" % (last_activity_delta.days)
				if last_activity_delta.days >= self.thresholds['critical']:
					out.status = 2
				elif last_activity_delta.days >= self.thresholds['warning']:
					out.status = 1
				else:
					out.status = 0
			else:
				out.content = "User hasn't yet logged in"
				out.status = 0
			out.exit()

def perfdata_dict_to_str(perfdata):
	variables = []
	for k, v in perfdata.iteritems():
		variables.append("%s=%s" % (k, ";".join([str(x) for x in v])))
	return " ".join(variables)


def get_thresholds():
	"""
	Return command line options for threshold values as dict
	"""
	thresholds = {
		'warning': 30, 
		'critical': 30
	}

	parser = OptionParser()
	parser.add_option('-c','--critical', dest = 'criticalValues')
	parser.add_option('-w','--warning', dest = 'warningValues') 

	(options, args) = parser.parse_args()

	if options.warningValues != None:
		match = options.warningValues.split(',')
		if len(match) == 2:
			thresholds['warning'] = int(match[0])
		else:
			thresholds['warning'] = int(options.warningValues)

	if options.criticalValues != None:
		match = options.criticalValues.split(',')
		if len(match) == 2:
			thresholds['critical'] = int(match[0])
		else:
			thresholds['critical'] = int(options.criticalValues)

	return thresholds

if __name__ == "__main__":
	plugin = CheckAtmoIdlePlugin(thresholds=get_thresholds())
	plugin.run()
