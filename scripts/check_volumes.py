#!/usr/bin/env python
from core.models import Identity
from api import get_esh_driver

def main():
    for ident in Identity.objects.filter(provider__id=1):
        driver = get_esh_driver(ident)
        try:
            vols = driver.list_volumes()
        except:
            print 'No volumes found for %s' % ident.created_by.username
        if not vols:
            continue
        print ('%s\n---\n' % ident.created_by.username)
        for vol in vols:
            print ('%s\t%s' %( vol.alias, vol.extra['createTime']))

if __name__ == "__main__":
    main()
