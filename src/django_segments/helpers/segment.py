"""Helper classes for segment operations.

These classes are used to create, update, and delete segments.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import models
from django.db import transaction
from django.utils import timezone

from django_segments.helpers.base import BaseHelper


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from django_segments.models import BaseSegment


class SegmentHelperBase(BaseHelper):
    """Base class for segment helpers."""

    def __init__(self, obj: BaseSegment):
        super().__init__(obj)
        self.config_dict = self.obj.span.get_config_dict()

    def validate_segment_range(self, segment_range):
        """Validate the segment range based on the span and any adjacent segments."""
        if segment_range.lower < self.obj.segment_range.lower or segment_range.upper > self.obj.segment_range.upper:
            raise ValueError("Segment range must be within the span's current range.")

    def get_annotated_segments(self):
        """Get all segments for the span annotated with additional information.

        (Consider extending to include custom/additional annotations)
        """
        return self.obj.__class__.objects.filter(span=self.obj).annotate(
            is_start=models.Case(
                models.When(segment_range__startswith=self.obj.segment_range.lower, then=True),
                default=False,
                output_field=models.BooleanField(),
            ),
            is_end=models.Case(
                models.When(segment_range__endswith=self.obj.segment_range.upper, then=True),
                default=False,
                output_field=models.BooleanField(),
            ),
        )

    def get_segment_class(self):
        """Get the segment class from the instance, useful when creating new segments dynamically."""
        return self.obj.__class__


class CreateSegmentHelper(SegmentHelperBase):
    """Helper class for creating segments."""

    @transaction.atomic
    def create(self, segment_range, *args, **kwargs):
        """Create a new Segment instance associated with the provided span and range.

        Adjusts the ranges and adjacent segments as needed.
        """
        self.validate_segment_range(segment_range)

        # Ensure no overlapping segments
        overlapping_segment = self.obj.__class__.objects.filter(
            span=self.obj, segment_range__overlap=segment_range
        ).exists()
        if overlapping_segment:
            raise ValueError("Cannot create segment: overlapping segments are not allowed.")

        segment_instance = self.obj.__class__.objects.create(
            span=self.obj, segment_range=segment_range, *args, **kwargs
        )

        # Adjust adjacent segments if not allowing segment gaps
        if not self.config_dict["allow_segment_gaps"]:
            self.adjust_adjacent_segments(segment_instance)

        return segment_instance

    def adjust_adjacent_segments(self):
        """Adjust the adjacent segments if not allowing segment gaps."""
        prev_segment = self.obj.previous
        next_segment = self.obj.next

        if prev_segment:
            prev_segment.segment_range = self.obj.set_upper_boundary(self.obj.segment_range.lower)
            prev_segment.save()

        if next_segment:
            next_segment.segment_range = self.obj.set_lower_boundary(self.obj.segment_range.upper)
            next_segment.save()
