from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "severity", "assigned_to", "created_at"]
    list_filter = ["status", "severity"]
