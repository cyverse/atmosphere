"""
  Database routers for atmosphere.
"""


class Service(object):
    """
    A router which allows the database to be configured in the model.
    """
    def db_for_read(self, model, **hints):
        if hasattr(model, 'connection_name'):
            return model.connection_name
        return None

    def db_for_write(self, model, **hints):
        if hasattr(model, 'connection_name'):
            return model.connection_name
        return None

    def allow_migrate(self, db, model):
        if hasattr(model, 'connection_name'):
            return model.connection_name == db
        return db == 'default'
