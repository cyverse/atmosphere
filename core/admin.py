from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.sessions.models import Session as DjangoSession
from django.utils import timezone

from threepio import logger

from core import email
from core import models
from core import tasks
from service.tasks import admin as admin_task


def private_object(modeladmin, request, queryset):
    queryset.update(private=True)
private_object.short_description = 'Make objects private True'


def end_date_object(modeladmin, request, queryset):
    queryset.update(end_date=timezone.now())
end_date_object.short_description = 'Add end-date to objects'


# For removing 'standard' registrations
admin.site.unregister(DjangoGroup)

@admin.register(models.NodeController)
class NodeControllerAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    list_display = ("alias", "hostname",
                    "start_date", "end_date",
                    "ssh_key_added")


@admin.register(models.MaintenanceRecord)
class MaintenanceAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    list_display = ("title", "provider", "start_date",
                    "end_date", "disable_login")


@admin.register(models.ApplicationVersion)
class ImageVersionAdmin(admin.ModelAdmin):
    search_fields = [
        "name","application__name",
        "machines__instance_source__identifier"
    ]
    actions = [end_date_object, ]
    list_display = (
        "id",
        "name",
        "application",
        "created_by",
        "start_date",
        "end_date",
    )

@admin.register(models.Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = (
        "__unicode__",
        "cpu",
        "memory",
        "storage",
        "storage_count",
    )


@admin.register(models.AllocationSource)
class AllocationSourceAdmin(admin.ModelAdmin):
    search_fields = [
        "name","source_id",
        "users__user__username"
    ]
    actions = [end_date_object, ]
    list_display = (
        "id",
        "name",
        "source_id",
        "compute_used",
        "compute_allowed",
    )

@admin.register(models.AllocationStrategy)
class AllocationStrategyAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Allocation)
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


@admin.register(models.InstanceSource)
class InstanceSourceAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = [
        "provider__location",
        "identifier"]
    list_display = ["identifier", "provider", "end_date"]
    list_filter = [
        "provider__location",
    ]


@admin.register(models.ProviderMachine)
class ProviderMachineAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = [
        "application_version__application__name",
        "instance_source__provider__location",
        "instance_source__identifier"]
    list_display = ["identifier", "_pm_provider", "start_date", "end_date"]
    list_filter = [
        "instance_source__provider__location",
        "application_version__application__private",
    ]

    def _pm_provider(self, obj):
        return obj.instance_source.provider.location

    def render_change_form(self, request, context, *args, **kwargs):
        return super(
            ProviderMachineAdmin,
            self).render_change_form(
            request,
            context,
            *args,
            **kwargs)


@admin.register(models.ApplicationVersionMembership)
class ApplicationVersionMembershipAdmin(admin.ModelAdmin):
    list_display = ["id", "_app_name", "_start_date", "_app_private", "group"]
    list_filter = [
        "image_version__application__name",
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
        context['adminform'].form.fields['application_version'].queryset = \
                models.ApplicationVersion.objects.order_by('application__name')
        context['adminform'].form.fields[
            'group'].queryset = models.Group.objects.order_by('name')
        return super(
            ApplicationVersionMembershipAdmin,
            self).render_change_form(
            request,
            context,
            *args,
            **kwargs)
    pass


@admin.register(models.ProviderMachineMembership)
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
    model = models.ProviderCredential
    extra = 1

@admin.register(models.EventTable)
class EventTableAdmin(admin.ModelAdmin):
    search_fields = ["entity_id", "name"]
    list_display = ["uuid", "name", "entity_id", "payload", "timestamp"]
    list_filter = ["entity_id", "name"]


@admin.register(models.Provider)
class ProviderAdmin(admin.ModelAdmin):
    inlines = [ProviderCredentialInline, ]
    actions = [end_date_object, ]
    list_display = ["location", "id", "provider_type", "active",
                    "public", "start_date", "end_date", "_credential_info"]
    list_filter = ["active", "public", "type__name"]

    def _credential_info(self, obj):
        return_text = ""
        for cred in obj.providercredential_set.order_by('key'):
            return_text += "<strong>%s</strong>:%s<br/>" % (
                cred.key, cred.value)
        return return_text
    _credential_info.allow_tags = True
    _credential_info.short_description = 'Provider Credentials'

    def provider_type(self, provider):
        if provider.type:
            return provider.type.name
        return None


@admin.register(models.Size)
class SizeAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = ["name", "alias", "provider__location"]
    list_display = ["name", "alias", "provider", "cpu", "mem", "disk",
                    "start_date", "end_date"]
    list_filter = ["provider__location"]


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name", "description"]


@admin.register(models.Volume)
class VolumeAdmin(admin.ModelAdmin):
    actions = [end_date_object, ]
    search_fields = ["instance_source__identifier", "name", "instance_source__provider__location", "instance_source__created_by__username"]
    list_display = ["identifier", "size", "provider",
                    "start_date", "end_date"]
    list_filter = ["instance_source__provider__location"]


@admin.register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    actions = [end_date_object, private_object]
    search_fields = [
        "name",
        "id",
        "versions__machines__instance_source__identifier"]
    list_display = [
        "uuid",
        "_current_machines",
        "name",
        "private",
        "created_by",
        "start_date",
        "end_date"]
    list_filter = [
        "end_date",
        "versions__machines__instance_source__provider",
    ]
    filter_vertical = ["tags", ]

    def save_model(self, request, obj, form, change):
        application = form.save(commit=False)
        application.save()
        form.save_m2m()
        if change:
            try:
                # TODO: Remove/Replace with 'glance_update_metadata'
                pass
            except Exception:
                logger.exception("Could not update metadata for application %s"
                                 % application)
        return application

    def render_change_form(self, request, context, *args, **kwargs):
        application = context['original']
        context['adminform'].form.fields['created_by_identity'].queryset = \
            models.Identity.objects.filter(created_by=application.created_by)
        return super(
            ApplicationAdmin,
            self).render_change_form(
            request,
            context,
            *args,
            **kwargs)


class CredentialInline(admin.TabularInline):
    model = models.Credential
    extra = 1


@admin.register(models.Identity)
class IdentityAdmin(admin.ModelAdmin):
    inlines = [CredentialInline, ]
    list_display = ("created_by", "provider", "_credential_info")
    search_fields = ["created_by__username"]
    list_filter = ["provider__location"]

    def _credential_info(self, obj):
        return_text = ""
        for cred in obj.credential_set.order_by('key'):
            return_text += "<strong>%s</strong>:%s<br/>" % (
                cred.key, cred.value)
        return return_text
    _credential_info.allow_tags = True
    _credential_info.short_description = 'Credentials'

    def save_model(self, request, obj, form, changed):
        obj.save()
        identity = obj
        admin_task.set_provider_quota.apply_async(
            args=[str(identity.uuid)])


class UserProfileInline(admin.StackedInline):
    model = models.UserProfile
    max_num = 1
    can_delete = False
    extra = 0
    verbose_name_plural = 'profile'


@admin.register(models.AtmosphereUser)
class UserAdmin(AuthUserAdmin):
    inlines = [UserProfileInline]
    fieldsets = AuthUserAdmin.fieldsets + (
        (None, {'fields': ('selected_identity', )}),
    )


@admin.register(models.IdentityMembership)
class IdentityMembershipAdmin(admin.ModelAdmin):
    search_fields = ["identity__created_by__username", ]
    list_display = ["_identity_user", "_identity_provider",
                    "quota", "allocation"]
    list_filter = ["identity__provider__location", "allocation"]

    def render_change_form(self, request, context, *args, **kwargs):
        identity_membership = context['original']
        # TODO: Change when created_by is != the user who 'owns' this
        # identity...
        user = identity_membership.identity.created_by
        context['adminform'].form.fields[
            'identity'].queryset = user.identity_set.all()
        context['adminform'].form.fields[
            'member'].queryset = user.group_set.all()
        return super(
            IdentityMembershipAdmin,
            self).render_change_form(
            request,
            context,
            *args,
            **kwargs)

    def _identity_provider(self, obj):
        return obj.identity.provider.location
    _identity_provider.short_description = 'Provider'

    def _identity_user(self, obj):
        return obj.identity.created_by.username
    _identity_user.short_description = 'Username'


@admin.register(models.ExportRequest)
class ExportRequestAdmin(admin.ModelAdmin):
    list_display = ["export_name", "export_owner_username",
                    "source_provider", "start_date", "end_date", "status",
                    "export_file"]

    def export_owner_username(self, export_request):
        return export_request.export_owner.username

    def source_provider(self, export_request):
        return export_request.source.provider


@admin.register(models.MachineRequest)
class MachineRequestAdmin(admin.ModelAdmin):
    search_fields = [
        "new_machine_owner__username",
        "new_machine__instance_source__identifier",
        "new_application_name",
        "instance__provider_alias"]
    list_display = [
        "new_application_name",
        "new_machine_owner",
        "instance_alias",
        "old_provider",
        "new_machine_provider",
        "start_date",
        "end_date",
        "status",
        "old_status",
        "opt_new_machine",
        "opt_parent_machine",
        "opt_machine_visibility"]
    list_filter = ["status"]

    # Overwrite
    def render_change_form(self, request, context, *args, **kwargs):
        machine_request = context['original']
        # TODO: Change when created_by is != the user who 'owns' this
        # identity...
        instance = machine_request.instance
        user = machine_request.new_machine_owner
        provider = machine_request.new_machine_provider
        parent_machine = models.ProviderMachine.objects.filter(
            instance_source__identifier=instance.source.identifier)
        new_machine = models.ProviderMachine.objects.filter(
                instance_source__provider=provider)

        admin_fields = context['adminform'].form.fields
        admin_fields['new_machine_owner'].queryset = provider.list_users()
        admin_fields['new_machine'].queryset = new_machine
        admin_fields['instance'].queryset = user.instance_set.all()
        # NOTE: Can't reliably refine 'parent_machine' -- Since the parent
        # could be from another provider.
        admin_fields['parent_machine'].queryset = parent_machine

        return super(MachineRequestAdmin, self).render_change_form(
            request,
            context,
            *args,
            **kwargs)

    def opt_machine_visibility(self, machine_request):
        if machine_request.new_application_visibility.lower() != 'public':
            return "%s\nUsers:%s" % (
                machine_request.new_application_visibility,
                machine_request.access_list
            )

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


@admin.register(models.InstanceStatusHistory)
class InstanceStatusHistoryAdmin(admin.ModelAdmin):
    search_fields = ["instance__created_by__username",
                     "instance__source__identifier",
                     "instance__provider_alias", "status__name"]
    list_display = ["instance_alias", "machine_alias", "instance_owner","instance_ip_address","status", "start_date", "end_date"]
    list_filter = ["instance__source__provider__location",
                   "status__name",
                   "instance__created_by__username"]
    ordering = ('-start_date',)

    def instance_owner(self, model):
        return model.instance.created_by.username

    def instance_ip_address(self, model):
        return model.instance.ip_address

    def machine_alias(self, model):
        return model.instance.source.identifier

    def instance_alias(self, model):
        return model.instance.provider_alias


@admin.register(models.Instance)
class InstanceAdmin(admin.ModelAdmin):
    search_fields = ["created_by__username", "provider_alias", "ip_address"]
    list_display = ["provider_alias", "get_size", "application_id", "application_name", "start_date", "name", "created_by", "ip_address"]
    list_filter = ["source__provider__location"]


@admin.register(DjangoSession)
class SessionAdmin(admin.ModelAdmin):

    def _session_data(self, obj):
        return obj.get_decoded()
    list_display = ['session_key', '_session_data', 'expire_date']
    search_fields = ["session_key", ]


@admin.register(models.AccountProvider)
class AccountProviderAdmin(admin.ModelAdmin):
    pass


@admin.register(models.CloudAdministrator)
class CloudAdminAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ["user", "provider", "uuid"]
    model = models.CloudAdministrator


@admin.register(models.ResourceRequest)
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
            identity = membership.identity
            identity.quota = obj.quota or identity.quota
            identity.save()
            # Marked for deletion
            membership.allocation = obj.allocation or membership.allocation
            membership.save()

            email_task = email.send_approved_resource_email(
                user=obj.created_by,
                request=obj.request,
                reason=obj.admin_message)

            admin_task.set_provider_quota.apply_async(
                args=[str(identity.uuid)],
                link=[tasks.close_request.si(obj), email_task],
                link_error=tasks.set_request_as_failed.si(obj))


@admin.register(models.Group)
class GroupAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid',)
    list_display = ('name', 'uuid',)
    list_filter = ['name', ]

@admin.register(models.EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    actions = None # disable the `delete selected` action

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.HelpLink)
class HelpLinkAdmin(admin.ModelAdmin):
    actions = None # disable the `delete selected` action
    list_display = ["link_key", "topic", "context", "href"]

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ("link_key", )
        return self.readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# For adding 'new' registrations
admin.site.register(models.ApplicationThreshold)
admin.site.register(models.Credential)
admin.site.register(models.ProviderType)
admin.site.register(models.ProviderInstanceAction)
