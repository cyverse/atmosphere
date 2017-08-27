from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator


class AbstractAdminPanel(admin.ModelAdmin):
    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        changelist_url_name = '%s_%s_changelist' % info
        urls = [
            url(r'^$', self.admin_site.admin_view(self.changelist_view), name=changelist_url_name),
        ]
        return urls

    @csrf_protect_m
    @method_decorator(staff_member_required)
    def changelist_view(self, request, extra_context=None):
        """
        The 'change list' admin view for a 'fake' model.

        Subclass this class and implement this method yourself if necessary.
        If you do, make sure to wrap it in these decorators:
        @csrf_protect_m
        @method_decorator(staff_member_required)
        """
        return self.model.admin_panel_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
