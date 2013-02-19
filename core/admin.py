from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup

from core.models.credential import Credential
from core.models.group import Group, IdentityMembership, ProviderMembership
from core.models.identity import Identity 
from core.models.instance import Instance
from core.models.machine import Machine, ProviderMachine
from core.models.machine_request import MachineRequest
from core.models.maintenance import MaintenanceRecord
from core.models.node import NodeController
from core.models.profile import UserProfile
from core.models.provider import Provider, ProviderType
from core.models.quota import Quota
from core.models.size import Size
from core.models.tag import Tag

class NodeControllerAdmin(admin.ModelAdmin):
  list_display = ("alias", "hostname","start_date","end_date","ssh_key_added")

class MaintenanceAdmin(admin.ModelAdmin):
  list_display = ("title","start_date","end_date","disable_login")

class MachineAdmin(admin.ModelAdmin):
  search_fields = ["name","id","location"]

class CredentialInline(admin.TabularInline):
    model = Credential
    extra = 1

class IdentityAdmin(admin.ModelAdmin):
    inlines = [
      CredentialInline,
    ]
    list_display = ("created_by", "provider","credential_info")
    search_fields = ["created_by__username",]
    def credential_info(self, obj):
        return_text = ""
        for cred in obj.credential_set.order_by('key'):
            return_text += "%s:%s " % (cred.key, cred.value)
	return return_text
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    can_delete = False
    extra = 0
    verbose_name_plural = 'profile'

class UserAdmin(AuthUserAdmin):
    inlines = [UserProfileInline]

admin.site.unregister(DjangoUser)
admin.site.register(DjangoUser, UserAdmin)

class ProviderMembershipAdmin(admin.ModelAdmin):
    search_fields = ["member__name",]

class IdentityMembershipAdmin(admin.ModelAdmin):
    search_fields = ["identity__created_by__username",]

class MachineRequestAdmin(admin.ModelAdmin):
    search_fields = ["created_by","instance__provider_alias"]

admin.site.register(Credential)
admin.site.unregister(DjangoGroup)
admin.site.register(Group)
admin.site.register(Identity, IdentityAdmin)
admin.site.register(IdentityMembership, IdentityMembershipAdmin)
admin.site.register(ProviderMembership, ProviderMembershipAdmin)
admin.site.register(Instance)
admin.site.register(Machine, MachineAdmin)
admin.site.register(MachineRequest, MachineRequestAdmin)
admin.site.register(MaintenanceRecord, MaintenanceAdmin)
admin.site.register(NodeController, NodeControllerAdmin)
admin.site.register(ProviderMachine)
admin.site.register(Provider)
admin.site.register(ProviderType)
admin.site.register(Quota)
admin.site.register(Size)
admin.site.register(Tag)
