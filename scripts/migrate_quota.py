from core.models import IdentityMembership, Quota as NewQuota
from service_old.models import Quota
old_quota = Quota.objects.all()
for q in old_quota:
    username = q.userid
    try:
        id = IdentityMembership.objects.get(member__name=username)
    except IdentityMembership.DoesNotExist, dne:
        print "Make %s an identity" % username
        continue
    try:
        new_quota = NewQuota.objects.get(user__username=username)
        new_quota.cpu = q.cpu
        new_quota.memory = q.memory/1024
        new_quota.save()
    except NewQuota.DoesNotExist, no_quota:
        new_quota = NewQuota.objects.create(user=User.objects.get(username=username), cpu=q.cpu, memory=q.memory/1024)
    id.quota = new_quota
    id.save()
