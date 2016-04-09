from __future__ import absolute_import
import logging


class InstanceAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        fields = "|".join([self.extra['instance_id'],
                           self.extra['ip_address'],
                           self.extra['username']])
        return '%s %s' % (fields, msg), kwargs


def create_instance_logger(logger, ip_address, username, instance_id):
    adapter = InstanceAdapter(logger, {'instance_id': instance_id,
                                       'ip_address': ip_address,
                                       'type': "atmo-deploy",
                                       'username': username})
    return adapter
