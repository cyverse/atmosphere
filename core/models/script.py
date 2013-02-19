"""

Script models for Atmosphere.

Known issues:
  Missing dependencies and orders

Work around:
  Scripts are independent, dependent scripts are merged.. No sense of order.
"""

from django.db import models


class Script(models.Model):
    """
    Scripts represent files located on the database to be used in configuration management
    Scripts are described by their name and version, as well as a description of what the script is doing
    """
    name = models.CharField(max_length=256) #nagios-nrpe.sh
    description = models.TextField() # ...
    version = models.IntegerField() #26
    location = models.FileField(upload_to="scripts") #scripts/atmo-init.rb
    def __unicode__(self):
        return "%s - %s" % (name, location.url)
    def pre_save():
        pass#Location.url = original+version (ex: /path/to/atmo-init.rb --> /path/to/atmo-init_26.rb) #WELL FORMATTED (Trim, tolower)
    def post_save():
        pass#Notify all packages 'script' belongs to
    class Meta:
        db_table = 'script'
        app_label = 'core'

class Package(models.Model):
    """
    Packages represent collecctions of scripts to be sent to an instance on-boot.
    Ideally a TAR package would be created and saved in 'location' containing all of the scripts to be run
    This may/may not stay when configuration management is introduced in Q4
    """
    name = models.CharField(max_length=256) #Atmosphere Package 27
    scripts = models.ManyToManyField(Script)
    sha1sum = models.CharField(max_length=50)
    location = models.FileField(upload_to="packages")
    def __unicode__(self):
        return "%s - %s" % (self.name, self.location.url)
    def notify():
        pass#Call self.save
    def pre_save():
        pass#Tar all scripts
            #sha1sum = hash
    class Meta:
        db_table = 'package'
        app_label = 'core'
"""
#TODO:
Here is the new atmo-init .PY
"Give me package 1" returns package.tar
unpack tar to new dir
chmod -r dir +x
run all files in dir
notify instance completed
"""
