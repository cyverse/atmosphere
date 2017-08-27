from django.contrib import admin

from core.admin_panel import AbstractAdminPanel
from jetstream import models
from jetstream.admin_panel import tas_api_panel


@admin.register(models.TASAllocationReport)
class TASReportAdmin(admin.ModelAdmin):
    search_fields = ["project_name", "username", ]
    list_display = ["id", "username", "project_name", "compute_used", "start_date", "end_date", "success"]
    list_filter = ["success", "project_name"]


@admin.register(tas_api_panel.TACCUserForXSEDEUsername)
class TACCUserForXSEDEUsernameAdminPanel(AbstractAdminPanel):
    pass


@admin.register(tas_api_panel.ActiveAllocations)
class ActiveAllocationsAdminPanel(AbstractAdminPanel):
    pass


@admin.register(tas_api_panel.ProjectsWithActiveAllocation)
class ProjectsWithActiveAllocationAdminPanel(AbstractAdminPanel):
    pass


@admin.register(tas_api_panel.ProjectsForUser)
class ProjectsForUserAdminPanel(AbstractAdminPanel):
    pass


@admin.register(tas_api_panel.UsersForProject)
class UsersForProjectAdminPanel(AbstractAdminPanel):
    pass
