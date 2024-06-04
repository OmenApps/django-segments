"""Models for the example app."""

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models

from django_segments.models import AbstractSegment
from django_segments.models import AbstractSpan


class XYZ:
    pass


class EventSpan(AbstractSpan):
    """A span of time that contains event segments."""

    class SpanConfig:
        """Configuration options for the span."""

        range_type = DateTimeRangeField

        allow_span_gaps = False
        # allow_segment_gaps = False
        # soft_delete = False

    def __str__(self):
        return f"Initial: {self.initial_range} - Current: {self.current_range}"


class EventSegment(AbstractSegment):
    """A segment of time within an event span."""

    class SegmentConfig:
        """Configuration options for the segment."""

        span_model = EventSpan

        previous_field_on_delete = models.CASCADE
        span_on_delete = models.SET_NULL

    def __str__(self):
        return f"Segment Range: {self.segment_range}"
