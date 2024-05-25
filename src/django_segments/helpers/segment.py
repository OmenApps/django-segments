import logging

from django.db import models
from django.db import transaction
from django.utils import timezone

from django_segments.helpers.base import BaseHelper


logger = logging.getLogger(__name__)


class SegmentHelperBase(BaseHelper):
    """Base class for segment helpers."""

    def __init__(self, obj):
        super().__init__(obj)
        self.config_dict = self.obj.span.get_config_dict()

    def validate_segment_range(self, span, segment_range):
        """Validate the segment range based on the span and any adjacent segments."""
        if segment_range.lower < span.current_range.lower or segment_range.upper > span.current_range.upper:
            raise ValueError("Segment range must be within the span's current range.")

    def get_annotated_segments(self, span):
        """Get all segments for the span annotated with additional information.

        (Consider extending to include custom/additional annotations)
        """
        return self.obj.__class__.objects.filter(segment_span=span).annotate(
            is_start=models.Case(
                models.When(segment_range_field__startswith=span.current_range.lower, then=True),
                default=False,
                output_field=models.BooleanField(),
            ),
            is_end=models.Case(
                models.When(segment_range_field__endswith=span.current_range.upper, then=True),
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
    def create(self, span, segment_range, *args, **kwargs):
        """Create a new Segment instance associated with the provided span and range.

        Adjusts the ranges and adjacent segments as needed.
        """
        self.validate_segment_range(span, segment_range)

        # Ensure no overlapping segments
        overlapping_segment = self.obj.__class__.objects.filter(
            segment_span=span, segment_range_field__overlap=segment_range
        ).exists()
        if overlapping_segment:
            raise ValueError("Cannot create segment: overlapping segments are not allowed.")

        segment_instance = self.obj.__class__.objects.create(
            segment_span=span, segment_range_field=segment_range, *args, **kwargs
        )

        # Adjust adjacent segments if sticky_boundaries is True
        if self.config_dict.get("sticky_boundaries", True):
            self.adjust_adjacent_segments(span, segment_instance)

        return segment_instance

    def adjust_adjacent_segments(self, span, segment):
        """Adjust the adjacent segments if sticky_boundaries is enabled."""
        prev_segment = segment.previous
        next_segment = segment.next

        if prev_segment:
            prev_segment.segment_range_field = span.set_upper_boundary(segment.segment_range_field.lower)
            prev_segment.save()

        if next_segment:
            next_segment.segment_range_field = span.set_lower_boundary(segment.segment_range_field.upper)
            next_segment.save()

    def validate_segment_range(self, span, segment_range):
        """Validate the segment range based on the span and any adjacent segments."""
        if segment_range.lower < span.current_range.lower or segment_range.upper > span.current_range.upper:
            raise ValueError("Segment range must be within the span's current range.")
