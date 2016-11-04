from django.contrib import admin
from jetstream import models

@admin.register(models.TASAllocationReport)
class TASReportAdmin(admin.ModelAdmin):
    search_fields = ["project_name", "username",]
    list_display = ["id", "username", "project_name", "compute_used", "start_date", "end_date", "success"]
    list_filter = ["success", "project_name"]
