"""Admin for the example project."""

from django.apps import apps
from django.contrib import admin

# from tests.example.models import EventSegment, EventSpan


# @admin.register(EventSpan)
# class EventSpanAdmin(admin.ModelAdmin):
#     """Admin for EventSpan model."""
#
#     list_display = ("id", "initial_range", "current_range", "deleted_at")
#     search_fields = ("id",)
#
#
# @admin.register(EventSegment)
# class EventSegmentAdmin(admin.ModelAdmin):
#     """Admin for EventSegment model."""
#
#     list_display = ("id", "segment_range", "span", "previous_segment", "deleted_at")
#     search_fields = ("id",)


# Autoregister any models not manually registered
class ListAdminMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        super().__init__(model, admin_site)


for model in apps.get_app_config("example").get_models():
    admin_class = type("AdminClass", (ListAdminMixin, admin.ModelAdmin), {})
    try:
        admin.site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        pass
