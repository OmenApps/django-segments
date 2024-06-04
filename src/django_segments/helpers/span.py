"""Helper classes for working with spans.

These classes are used to create, update, and delete spans.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from typing import Union

from django.db import transaction
from django.utils import timezone
from psycopg2.extras import Range  # psycopg2's base range class

from django_segments.helpers.base import BaseHelper
from django_segments.models.base import SpanConfigurationHelper
from django_segments.signals import segment_post_create
from django_segments.signals import segment_post_delete
from django_segments.signals import segment_post_delete_or_soft_delete
from django_segments.signals import segment_post_soft_delete
from django_segments.signals import segment_post_update
from django_segments.signals import segment_pre_create
from django_segments.signals import segment_pre_delete
from django_segments.signals import segment_pre_delete_or_soft_delete
from django_segments.signals import segment_pre_soft_delete
from django_segments.signals import segment_pre_update
from django_segments.signals import span_post_create
from django_segments.signals import span_post_delete
from django_segments.signals import span_post_delete_or_soft_delete
from django_segments.signals import span_post_soft_delete
from django_segments.signals import span_post_update
from django_segments.signals import span_pre_create
from django_segments.signals import span_pre_delete
from django_segments.signals import span_pre_delete_or_soft_delete
from django_segments.signals import span_pre_soft_delete
from django_segments.signals import span_pre_update


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django_segments.models import BaseSpan


class SpanHelperBase(BaseHelper):  # pylint: disable=R0903
    """Base class for span helpers."""

    def __init__(self, obj: BaseSpan):
        super().__init__(obj)
        self.config_dict = SpanConfigurationHelper.get_config_dict(obj)


class CreateSpanHelper:
    """Helper class for creating spans.

    Does not inherit from BaseHelper because there is initially no object to work with.
    """

    def __init__(self, model_class: type[BaseSpan]):
        self.model_class = model_class
        self.config_dict = SpanConfigurationHelper.get_config_dict(model_class)

    @transaction.atomic
    def create(self, *args, range_value: Range = None, **kwargs):
        """Create a new Span instance with initial_range and current_range fields set.

        Optionally create an initial Segment that spans the entire range if needed.
        """
        # Initialize range values in kwargs
        kwargs.update({"initial_range": range_value, "current_range": range_value})

        # Create the Span instance
        span_pre_create.send(sender=self.model_class)  # Send signal
        span_instance = self.model_class.objects.create(*args, **kwargs)
        span_post_create.send(sender=self.model_class, instance=span_instance)  # Send signal

        segment_class = span_instance.get_segment_class()

        # Create an initial Segment of the same length as the span if not allowed to have gaps
        if not self.config_dict.get("allow_span_gaps", True):
            segment_pre_create.send(sender=segment_class)  # Send signal
            segment = self.create_initial_segment(span_instance)
            segment_post_create.send(sender=segment_class, instance=segment)  # Send signal

        return span_instance

    def create_initial_segment(self, obj):
        """Create an initial Segment that spans the entire range of the Span."""
        segment_class = obj.get_segment_class()
        segment_range = obj.current_range
        segment = segment_class.objects.create(span=obj, segment_range=segment_range)
        return segment


class ShiftSpanHelper(SpanHelperBase):
    """Helper class for shifting spans."""

    @transaction.atomic
    def shift_by_value(self, value: Union[int, Decimal, timezone.timedelta]):
        """Shift the range value of the entire Span and each of its associated Segments by the given value.

        Args:
            value (int, Decimal, datetime.timedelta, or other appropriate type): The value by which to shift the range.
        """
        # Validate the value type
        self.validate_value_type(value)

        # Shift the current_range of the Span
        span_pre_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal
        self.obj.current_range = self.shift_range(self.obj.current_range, value)

        # Get all segments and shift their ranges
        segments = self.obj.get_segments()
        for segment in segments:
            segment_pre_update.send(
                sender=segment.__class__, instance=segment, segment_range=segment.segment_range
            )  # Send signal
            segment.segment_range = self.shift_range(segment.segment_range, value)
            segment.save()
            segment_post_update.send(
                sender=segment.__class__, instance=segment, segment_range=segment.segment_range
            )  # Send signal

        self.obj.save()
        span_post_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal

    def shift_range(self, range_field: Range, value: Union[int, Decimal, timezone.timedelta]) -> Range:
        """Shift the given range field by the specified value.

        Args:
            range_field (Range): The range field to shift.
            value (int, float, datetime.timedelta, or other appropriate type): The value by which to shift the range.

        Returns:
            Range: The shifted range.
        """
        return range_field.__class__(
            lower=range_field.lower + value,
            upper=range_field.upper + value,
        )


class ShiftLowerSpanHelper(SpanHelperBase):
    """Helper class for shifting the lower boundary of a span."""

    @transaction.atomic
    def shift_lower_by_value(self, value: Union[int, Decimal, timezone.timedelta]):
        """Shift the lower boundary of the Span's current_range by the given value.

        Args:
            value (int, float, datetime.timedelta, or other appropriate type): The value by which to shift the lower boundary.
        """
        # Validate the value type
        self.validate_value_type(value)

        segments = self.obj.get_segments()

        # Get the lowest segment
        lowest_segment = segments.earliest("segment_range__lower")

        # Calculate the new lower boundary
        new_lower = self.obj.current_range.lower + value

        # Ensure the new lower boundary is not greater than or equal to the upper boundary of the lowest segment
        if new_lower >= lowest_segment.segment_range.lower:
            raise ValueError(
                "The new lower boundary cannot be greater than or equal to the lowest segment's lower boundary."
            )

        # Shift the lower boundary of the Span
        span_pre_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal
        self.obj.set_lower_boundary(new_lower)

        # Adjust the lowest segment if we don't allow span gaps
        if not self.config_dict.get("allow_span_gaps", True):
            segment_pre_update.send(
                sender=lowest_segment.__class__,
                instance=lowest_segment,
                segment_range=lowest_segment.segment_range,
            )  # Send signal
            lowest_segment.set_lower_boundary(new_lower)
            lowest_segment.save()
            segment_post_update.send(
                sender=lowest_segment.__class__,
                instance=lowest_segment,
                segment_range=lowest_segment.segment_range,
            )  # Send signal

        self.obj.save()
        span_post_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal


class ShiftUpperSpanHelper(SpanHelperBase):
    """Helper class for shifting the upper boundary of a span."""

    @transaction.atomic
    def shift_upper_by_value(self, value: Union[int, Decimal, timezone.timedelta]):
        """Shift the upper boundary of the Span's current_range by the given value.

        Args:
            value (int, float, datetime.timedelta, or other appropriate type): The value by which to shift the upper boundary.
        """
        # Validate the value type
        self.validate_value_type(value)

        segments = self.obj.get_segments()

        # Get the highest segment
        highest_segment = segments.latest("segment_range__upper")

        # Calculate the new upper boundary
        new_upper = self.obj.current_range.upper + value

        # Ensure the new upper boundary is not less than or equal to the lower boundary of the highest segment
        if new_upper <= highest_segment.segment_range.upper:
            raise ValueError(
                "The new upper boundary cannot be less than or equal to the highest segment's upper boundary."
            )

        # Shift the upper boundary of the Span
        span_pre_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal
        self.obj.set_upper_boundary(new_upper)

        # Adjust the highest segment if not allowing span gaps
        if not self.config_dict.get("allow_span_gaps", True):
            segment_pre_update.send(
                sender=highest_segment.__class__,
                instance=highest_segment,
                segment_range=highest_segment.segment_range,
            )  # Send signal
            highest_segment.set_upper_boundary(new_upper)
            highest_segment.save()
            segment_post_update.send(
                sender=highest_segment.__class__,
                instance=highest_segment,
                segment_range=highest_segment.segment_range,
            )  # Send signal

        self.obj.save()
        span_post_update.send(
            sender=self.obj.__class__, instance=self.obj, current_range=self.obj.current_range
        )  # Send signal


class ShiftLowerToValueSpanHelper(SpanHelperBase):
    """Helper class for shifting the lower boundary of a span to a specific value."""

    @transaction.atomic
    def shift_lower_to_value(self, new_value: Union[int, Decimal, timezone.datetime, timezone.datetime.date]):
        """Shift the lower boundary of the Span's current_range to the given value.

        Args:
            new_value (int, float, datetime, or other appropriate type): The new value for the lower boundary.
        """
        # Validate the value type
        self.validate_value_type(new_value)

        # Calculate the difference
        current_lower = self.obj.current_range.lower
        value_difference = new_value - current_lower

        # Shift the lower boundary by the difference
        ShiftLowerSpanHelper(self.obj).shift_lower_by_value(value_difference)


class ShiftUpperToValueSpanHelper(SpanHelperBase):
    """Helper class for shifting the upper boundary of a span to a specific value."""

    @transaction.atomic
    def shift_upper_to_value(self, new_value: Union[int, Decimal, timezone.datetime, timezone.datetime.date]):
        """Shift the upper boundary of the Span's current_range to the given value.

        Args:
            new_value (int, float, datetime, or other appropriate type): The new value for the upper boundary.
        """
        # Validate the value type
        self.validate_value_type(new_value)

        # Calculate the difference
        current_upper = self.obj.current_range.upper
        value_difference = new_value - current_upper

        # Shift the upper boundary by the difference
        ShiftUpperSpanHelper(self.obj).shift_upper_by_value(value_difference)


class DeleteSpanHelper(SpanHelperBase):
    """Helper class for deleting spans."""

    @transaction.atomic
    def delete(self):
        """Delete the Span and its associated Segments.

        If soft_delete is True, mark the Span and its Segments as deleted.
        If soft_delete is False, perform a hard delete.
        """
        segments = self.obj.get_segments()

        if self.config_dict.get("soft_delete", True):
            # Soft delete: mark the Span and its Segments as deleted
            current_time = timezone.now()

            span_pre_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal
            span_pre_soft_delete.send(sender=self.obj.__class__, instance=self.obj)  # Send signal
            self.obj.deleted_at = current_time

            for segment in segments:
                segment_pre_delete_or_soft_delete.send(sender=segment.__class__)  # Send signal
                segment_pre_soft_delete.send(sender=segment.__class__, instance=segment)  # Send signal
                segment.deleted_at = current_time
                segment.save()
                segment_post_soft_delete.send(sender=segment.__class__, instance=segment)  # Send signal
                segment_post_delete_or_soft_delete.send(sender=segment.__class__)  # Send signal

            self.obj.save()
            span_post_soft_delete.send(sender=self.obj.__class__, instance=self.obj)  # Send signal
            span_post_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal
        else:
            # Hard delete: delete the Span and its Segments
            span_pre_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal
            span_pre_delete.send(sender=self.obj.__class__)  # Send signal

            segment_pre_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal
            segment_pre_delete.send(sender=self.obj.__class__)
            segments.delete()
            segment_post_delete.send(sender=self.obj.__class__)  # Send signal
            segment_post_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal

            self.obj.delete()
            span_post_delete.send(sender=self.obj.__class__)  # Send signal
            span_post_delete_or_soft_delete.send(sender=self.obj.__class__)  # Send signal
