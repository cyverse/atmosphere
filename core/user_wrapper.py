from atmosphere.core.models.group import Group as CoreGroup
from core.models import AtmosphereUser as User


def convert_group(dgroup):
    return CoreGroup.objects.get(group_ptr_id=dgroup.pk)


class UserWrapper():

    """
    Use this to collect all relevant group information for a user
    """
    user = None
    provider = None

    def __init__(self, user_obj, provider_obj):
        if not isinstance(user_obj, User) and isinstance(user_obj, ""):
            user_obj = User.objects.get(username=user_obj)
        else:
            raise Exception("Expected User OR String, got %s" % type(user_obj))
        self.user = user_obj
        self.provider = provider_obj

    def all_groups(self, leader=False):
        django_groups = self.user.groups.all()
        core_groups = []
        for dgroup in django_groups:
            coregroup = convert_group(dgroup)
            if leader and self.user not in coregroup.leaders.all():
                continue
            core_groups.append(coregroup)
        return core_groups

    def all_machines(self):
        groups = self.all_groups()
        machine_list = []
        for group in groups:
            machine_list.extend(
                [mach for mach
                 in group.applications.all()
                 if mach not in machine_list
                 and len(mach.providers.filter(id=self.provider.id)) == 1])
        return machine_list

    def all_instances(self):
        groups = self.all_groups()
        instance_list = []
        for group in groups:
            instance_list.extend(
                [instance for instance
                 in group.instances.all()
                 if instance not in instance_list
                 and instance.provider_machine.provider == self.provider])
        return instance_list

    def all_identities(self):
        groups = self.all_groups(leader=True)
        identity_list = []
        for group in groups:
            identity_list.extend(
                [ident for ident
                 in group.identities.all()
                 if ident not in identity_list
                 and ident.provider == self.provider])
        return identity_list
