#!/usr/bin/env python
from core.models.machine import filter_core_machine, convert_esh_machine, create_application
from core.models import Identity, Provider
from api import get_esh_driver
from core.models import Application

def main():
    driver = get_esh_driver(Identity.objects.get(provider__id=4, created_by__username='sgregory'))
    for app in Application.objects.all():
        pms = app.providermachine_set.filter(provider__id=4)
        if len(pms) >= 2:
            for pm in pms:
                print "%s shares application %s" % (pm.identifier, app.name)
                mach = driver.get_machine(pm.identifier)
                if not mach:
                    print "%s doesnt exist" % pm.identifier
                    continue
                if mach.name != app.name:
                     new_app = create_application(pm.identifier, 4, mach.name)
                     pm.application = new_app
                     pm.save()
                     print 'New app created:%s' % new_app.name

if __name__ == "__main__":
    main()
