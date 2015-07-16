from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.forms import UserChangeForm
from django.contrib.sessions.models import Session as DjangoSession
from django.utils import timezone

from core.models.abstract import InstanceSource
from core.models.application import Application
from core.models.cloud_admin import CloudAdministrator
from core.models.credential import Credential, ProviderCredential
from core.models.export_request import ExportRequest
from core.models.group import Group, IdentityMembership
from core.models.identity import Identity
from core.models.instance import Instance, InstanceStatusHistory
from core.models.machine import ProviderMachine, ProviderMachineMembership
from core.models.machine_request import MachineRequest
from core.models.maintenance import MaintenanceRecord
from core.models.node import NodeController
from core.models.profile import UserProfile
from core.models.provider import Provider, ProviderType, AccountProvider
from core.models.quota import Quota
from core.models.allocation_strategy import Allocation, AllocationStrategy
from core.models.resource_request import ResourceRequest
from core.models.size import Size
from core.models.tag import Tag
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.models.version import ApplicationVersion, ApplicationVersionMembership

from threepio import logger

def private_object(modeladmin, request, queryset):
        queryset.update(private=True)
private_object.short_description = 'Make objects private True'

def end_date_object(modeladmin, request, queryset):
        queryset.update(end_date=timezone.now())
end_date_object.short_description = 'Add end-date to objects'


@admin.register(NodeController)
class NodeControllerAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    list_display = ("alias", "hostname",
                    "start_date", "end_date",
                    "ssh_key_added")


@admin.register(MaintenanceRecord)
class MaintenanceAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    list_display = ("title", "provider", "start_date",
                    "end_date", "disable_login")


@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = ("__unicode__", "cpu", "memory", "storage", "storage_count", "suspended_count")


@admin.register(AllocationStrategy)
class AllocationStrategyAdmin(admin.ModelAdmin):
    pass


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):

    list_display = ("threshold_str", "delta_str")

    def threshold_str(self, obj):
        td = timedelta(minutes=obj.threshold)
        return '%s days, %s hours, %s minutes' % (td.days,
                                                  td.seconds // 3600,
                                                  (td.seconds // 60) % 60)
    threshold_str.short_description = 'Threshold'

    def delta_str(self, obj):
        td = timedelta(minutes=obj.delta)
        return '%s days, %s hours, %s minutes' % (td.days,
                                                  td.seconds // 3600,
                                                  (td.seconds // 60) % 60)
    delta_str.short_description = 'Delta'


@admin.register(ProviderMachine)
class ProviderMachineAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = ["application_version__application__name", "instance_source__provider__location", "instance_source__identifier"]
    list_display = ["identifier", "_pm_provider", "end_date"]
    list_filter = [
        "instance_source__provider__location",
        "application_version__application__private",
    ]

    def _pm_provider(self, obj):
        return obj.instance_source.provider.location

    def render_change_form(self, request, context, *args, **kwargs):
        pm = context['original']
        return super(ProviderMachineAdmin, self).render_change_form(request, context, *args, **kwargs)


@admin.register(ApplicationVersionMembership)
class ApplicationVersionMembershipAdmin(admin.ModelAdmin):
    list_display = ["id", "_app_name", "_start_date", "_app_private", "group"]
    list_filter = [
            "application_version__application__name",
            "group__name"
            ]
    def _start_date(self, obj):
        return obj.application_version.start_date
    def _app_private(self, obj):
        return obj.application_version.application.private
    _app_private.boolean = True
    def _app_name(self, obj):
        return obj.application_version

    def render_change_form(self, request, context, *args, **kwargs):
        application = context['original']
        context['adminform'].form.fields['application_version'].queryset = ApplicationVersion.objects.order_by('application__name')
        context['adminform'].form.fields['group'].queryset = Group.objects.order_by('name')
        return super(ApplicationVersionMembershipAdmin, self).render_change_form(request, context, *args, **kwargs)
    pass

@admin.register(ProviderMachineMembership)
class ProviderMachineMembershipAdmin(admin.ModelAdmin):
    list_display = ["id", "_pm_provider", "_pm_identifier", "_pm_name",
                    "_pm_private", "group"]
    list_filter = [
            "provider_machine__instance_source__provider__location",
            "provider_machine__instance_source__identifier",
            "group__name"
            ]
    def _pm_provider(self, obj):
        return obj.provider_machine.provider.location
    def _pm_private(self, obj):
        return obj.provider_machine.application_version.application.private
    _pm_private.boolean = True
    def _pm_identifier(self, obj):
        return obj.provider_machine.identifier
    def _pm_name(self, obj):
        return obj.provider_machine.application_version.application.name
    pass

class ProviderCredentialInline(admin.TabularInline):
    model = ProviderCredential
    extra = 1


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    inlines = [ProviderCredentialInline, ]
    actions = [end_date_object, ]
    list_display = ["location", "id", "provider_type", "active",
                    "public", "start_date", "end_date", "_credential_info"]
    list_filter = ["active", "public", "type__name"]
    def _credential_info(self, obj):
        return_text = ""
        for cred in obj.providercredential_set.order_by('key'):
            return_text += "<strong>%s</strong>:%s<br/>" % (cred.key, cred.value)
        return return_text
    _credential_info.allow_tags = True
    _credential_info.short_description = 'Provider Credentials'

    def provider_type(self, provider):
        if provider.type:
            return provider.type.name
        return None


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = ["name", "alias", "provider__location"]
    list_display = ["name", "provider", "cpu", "mem", "disk",
                    "start_date", "end_date"]
    list_filter = ["provider__location"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name", "description"]


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = ["identifier", "name", "location"]
    list_display = ["identifier", "size", "provider",
            "start_date", "end_date"]
    list_filter = ["instance_source__provider__location"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    actions = [end_date_object, private_object]
    search_fields = ["name", "id", "versions__machines__instance_source__identifier"]
    list_display = ["uuid", "_current_machines", "name", "private", "created_by", "start_date", "end_date" ]
    filter_vertical = ["tags",]

    def save_model(self, request, obj, form, change):
        user = request.user
        application = form.save(commit=False)
        application.save()
        form.save_m2m()
        if change:
            try:
                save_app_to_metadata(application)
            except Exception, e:
                logger.exception("Could not update metadata for application %s"
                                 % application)
        return application

    def render_change_form(self, request, context, *args, **kwargs):
        application = context['original']
        context['adminform'].form.fields['created_by_identity'].queryset = Identity.objects.filter(created_by=application.created_by)
        return super(ApplicationAdmin, self).render_change_form(request, context, *args, **kwargs)

class CredentialInline(admin.TabularInline):
    model = Credential
    extra = 1


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    inlines = [CredentialInline, ]
    list_display = ("created_by", "provider", "_credential_info")
    search_fields = ["created_by__username"]
    list_filter = ["provider__location"]

    def _credential_info(self, obj):
        return_text = ""
        for cred in obj.credential_set.order_by('key'):
            return_text += "<strong>%s</strong>:%s<br/>" % (cred.key, cred.value)
        return return_text
    _credential_info.allow_tags = True
    _credential_info.short_description = 'Credentials'


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    can_delete = False
    extra = 0
    verbose_name_plural = 'profile'


@admin.register(AtmosphereUser)
class UserAdmin(AuthUserAdmin):
    inlines = [UserProfileInline]
    fieldsets = AuthUserAdmin.fieldsets + (
        (None, {'fields': ('selected_identity', )}),
    )


@admin.register(IdentityMembership)
class IdentityMembershipAdmin(admin.ModelAdmin):
    search_fields = ["identity__created_by__username", ]
    list_display = ["_identity_user", "_identity_provider",
                    "quota", "allocation"]
    list_filter = ["identity__provider__location", "allocation"]

    def render_change_form(self, request, context, *args, **kwargs):
        identity_membership = context['original']
        #TODO: Change when created_by is != the user who 'owns' this identity...
        user = identity_membership.identity.created_by
        context['adminform'].form.fields['identity'].queryset = user.identity_set.all()
        context['adminform'].form.fields['member'].queryset = user.group_set.all()
        return super(IdentityMembershipAdmin, self).render_change_form(request, context, *args, **kwargs)

    def _identity_provider(self, obj):
        return obj.identity.provider.location
    _identity_provider.short_description = 'Provider'

    def _identity_user(self, obj):
        return obj.identity.created_by.username
    _identity_user.short_description = 'Username'

@admin.register(ExportRequest)
class ExportRequestAdmin(admin.ModelAdmin):
    list_display = ["export_name", "export_owner_username",
    "source_provider", "start_date", "end_date", "status",
    "export_file"]

    def export_owner_username(self, export_request):
        return export_request.export_owner.username

    def source_provider(self, export_request):
        return export_request.source.provider

@admin.register(MachineRequest)
class MachineRequestAdmin(admin.ModelAdmin):
    search_fields = ["new_machine_owner__username", "new_application_name", "instance__provider_alias"]
    list_display = ["new_application_name", "new_machine_owner", "instance_alias",
                    "old_provider", "new_machine_provider",
		    "start_date", "end_date", "status",
		    "opt_new_machine", "opt_parent_machine", "opt_machine_visibility"]
    list_filter = ["status"]

    #Overwrite
    def render_change_form(self, request, context, *args, **kwargs):
        machine_request = context['original']
        #TODO: Change when created_by is != the user who 'owns' this identity...
        instance = machine_request.instance
        user = machine_request.new_machine_owner
        provider = machine_request.new_machine_provider
        context['adminform'].form.fields['new_machine_owner'].queryset = provider.list_users()
        context['adminform'].form.fields['new_machine'].queryset = ProviderMachine.objects.filter(instance_source__provider=provider)
        context['adminform'].form.fields['instance'].queryset = user.instance_set.all()
        #NOTE: Can't reliably refine 'parent_machine' -- Since the parent could be from another provider.
        context['adminform'].form.fields['parent_machine'].queryset = ProviderMachine.objects.filter(instance_source__identifier=instance.source.identifier)

        return super(MachineRequestAdmin, self).render_change_form(request, context, *args, **kwargs)

    def opt_machine_visibility(self, machine_request):
        if machine_request.new_application_visibility.lower() != 'public':
            return "%s\nUsers:%s" % (machine_request.new_application_visibility,
                                        machine_request.access_list)
        return machine_request.new_application_visibility
    opt_machine_visibility.allow_tags = True

    def opt_parent_machine(self, machine_request):
        if machine_request.parent_machine:
            return machine_request.parent_machine.identifier
        return None

    def opt_new_machine(self, machine_request):
        if machine_request.new_machine:
            return machine_request.new_machine.identifier
        return None


@admin.register(InstanceStatusHistory)
class InstanceStatusHistoryAdmin(admin.ModelAdmin):
    search_fields = ["instance__created_by__username",
            "instance__provider_alias", "status__name"]
    list_display = ["instance_alias", "status", "start_date", "end_date"]
    list_filter = ["instance__source__provider__location",
                   "status__name",
                   "instance__created_by__username" ]
    ordering = ('-start_date',)
    def instance_alias(self, model):
        return model.instance.provider_alias


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    search_fields = ["created_by__username", "provider_alias", "ip_address"]
    list_display = ["provider_alias", "name", "created_by", "ip_address"]
    list_filter = ["source__provider__location"]


@admin.register(DjangoSession)
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()
    list_display = ['session_key', '_session_data', 'expire_date']
    search_fields = ["session_key", ]


@admin.register(AccountProvider)
class AccountProviderAdmin(admin.ModelAdmin):
    pass


@admin.register(CloudAdministrator)
class CloudAdminAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ["user", "provider", "uuid"]
    model = CloudAdministrator


@admin.register(ResourceRequest)
class ResourceRequestAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'created_by', 'request', 'description',
                       'start_date', 'end_date')
    list_display = ("request", "status", "created_by", "start_date",
                    "end_date", "allocation", "quota")

    list_filter = ["status", "membership__identity__provider__location"]
    exclude = ("membership",)

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, changed):
        obj.end_date = timezone.now()
        obj.save()

        if obj.is_approved():
            membership = obj.membership
            membership.allocation = obj.allocation
            membership.quota = obj.quota
            membership.save()
            membership.approve_quota(obj.id)

#For adding 'new' registrations
admin.site.register(Credential)
admin.site.register(Group)
admin.site.register(ProviderType)

#For removing 'standard' registrations
admin.site.unregister(DjangoGroup)
