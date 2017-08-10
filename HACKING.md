# HACKING.md

This guide has a collection of tips for developing on Atmosphere.

### Prefetch data in views with nested serializers

If you suspect that a view is making too many database queries, read this tip.
The solution is to prefetch model instances, so that serializers re-use
already fetched models, rather than always fetching their own.

Suppose there are 400 Cars. Each Car has a Manufacturer, and the serializer
for a Car has a single field, ManufacturerSerializer. We want to write an
efficient view that returns all 400 cars each with its manufacturer.

##### Without prefetching
During serialization of the view, there will be 1 database query for 400 `Car`s. The Manufacturer serializer will be passed a reference like `car.manufacturer`. If this is the first time that the property has been accessed on the instance, then a database query will fetch the corresponding value from the `Manufacturer` table. Here lies the problem. For each `Car` a `Manufacturer` will be fetched. In total 401 queries will be made. This is an n+1 problem.

##### With prefetching
There will be 1 query for 400 `Car`s and 1 query for each related `Manufacturer`.
In this case, the view for Car would override it's `get_queryset` method:
```python
def get_queryset(self):
    queryset = Car.objects.all()
    return queryset.select_related("manufacturer")
```
A Car model returned from this queryset, will have its `manufacturer`
attribute already fetched.

Caveat:
`select_related` only works with single-valued relationships (i.e. ForeignKey,
one-to-one). For multi-valued relationships see `prefetch_related`.

Resources:
- [select_related](https://docs.djangoproject.com/en/1.10/ref/models/querysets/#django.db.models.query.QuerySet.prefetch_related)
- [prefetch_related](https://docs.djangoproject.com/en/1.10/ref/models/querysets/#select-related)
- [whats-the-difference-between-select-related-and-prefetch-related-in-django-orm](https://stackoverflow.com/questions/31237042/whats-the-difference-between-select-related-and-prefetch-related-in-django-orm/45377282)

### Log all database queries with timing information

If you're trying to step through code and figure out why (and when) queries are being
executed, it's useful to add database logging. It's as simple as whenever a
query is made, the query will be printed in the process where atmosphere is
running.

This will slow down your application, but can be tremendously handy. Add the
following to `atmosphere/settings/local.py`:
```python
LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'handlers': {
        'console': {
            # logging handler that outputs log messages to terminal
            'class': 'logging.StreamHandler',
            'level': 'DEBUG', # message level to be written to console
        },
    },
    'loggers': {
        '': {
            # this sets root level logger to log debug and higher level
            # logs to console. All other loggers inherit settings from
            # root level logger.
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False, # this tells logger to send logging message
                                # to its parent (will send if set to True)
        },
        'django.db': {
            'level': 'DEBUG'
        },
    },
}
```
