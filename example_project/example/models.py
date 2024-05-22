"""Models for the example app."""

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models

from django_segments.models import AbstractSegment
from django_segments.models import AbstractSpan


class EventSpan(AbstractSpan):
    """A span of time that contains event segments."""

    initial_range = DateTimeRangeField()
    current_range = DateTimeRangeField()

    class Meta:  # pylint: disable=missing-class-docstring
        abstract = False

    def __str__(self):
        return f"Initial: {self.initial_range} - Current: {self.current_range}"


class EventSegment(AbstractSegment):
    """A segment of time within an event span."""

    event_span = models.ForeignKey(EventSpan, on_delete=models.CASCADE)
    segment_range = DateTimeRangeField()

    # If a field name other than `segment_range` is used for the range field, it should be specified like this:
    segment_range_field = "segment_range"

    class Meta:  # pylint: disable=missing-class-docstring
        abstract = False

    def __str__(self):
        return f"Segment Range: {self.segment_range}"
