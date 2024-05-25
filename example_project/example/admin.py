"""Admin for the example project."""

from django.contrib import admin

from .models import EventSegment
from .models import EventSpan


@admin.register(EventSpan)
class EventSpanAdmin(admin.ModelAdmin):
    """Admin for EventSpan model."""

    list_display = ("id", "initial_range", "current_range", "deleted_at")
    search_fields = ("id",)


@admin.register(EventSegment)
class EventSegmentAdmin(admin.ModelAdmin):
    """Admin for EventSegment model."""

    list_display = ("id", "segment_range", "event_span", "previous_segment", "deleted_at")
    search_fields = ("id",)
