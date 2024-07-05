"""Helper classes for segment operations.

These classes are used to create, update, and delete segments.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Union

from django.db import models, transaction
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
    Range,
)
from django.utils import timezone

from django_segments.context_managers import (
    SegmentCreateSignalContext,
    SegmentDeleteSignalContext,
    SegmentSoftDeleteSignalContext,
    SegmentUpdateSignalContext,
    SpanCreateSignalContext,
    SpanDeleteSignalContext,
    SpanSoftDeleteSignalContext,
    SpanUpdateSignalContext,
)
from django_segments.helpers.base import BaseHelper, BoundaryType
from django_segments.helpers.span import ExtendSpanHelper
from django_segments.models.base import SegmentConfigurationHelper


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from django_segments.models import AbstractSegment, AbstractSpan


class CreateSegmentHelper:
    """Helper class for creating a new segment.

    An exception will be raised if the proposed segment range overlaps with any existing segments.

    Usage:

    .. code-block:: python

        segment = CreateSegmentHelper(
            span=span_instance,
            segment_range=NumericRange(0, 10),
            field1="value1",
            field2="value2",
        ).create()
    """

    def __init__(
        self,
        *,
        span: AbstractSpan,
        segment_range: Union[Range, DateRange, DateTimeTZRange, NumericRange],
        **kwargs,
    ):
        self.span = span
        self.segment_range = segment_range
        self.segment_instance = None
        self.sement_class = self.span.get_segment_class()

        self.kwargs = kwargs

    @transaction.atomic
    def create(self):
        """Create a new Segment instance associated with the provided span and range.

        Adjusts the ranges and adjacent segments as needed.
        """
        # Ensure no overlapping segments
        overlapping_segments = self.sement_class.objects.filter(
            span=self.span, segment_range__overlap=self.segment_range
        )

        if overlapping_segments.exists():
            raise ValueError(
                "Cannot create segment: proposed range overlaps with the following existing segment(s): "
                f"{overlapping_segments}"
            )

        self.segment_instance = self.sement_class(span=self.span, segment_range=self.segment_range, **self.kwargs)

        with SpanUpdateSignalContext(self.span):
            with SegmentCreateSignalContext(span=self.span, segment_range=self.segment_range, **self.kwargs) as context:
                # Extend the span to include the new segment range if needed
                helper = ExtendSpanHelper(self.span)
                helper.extend_to(value=self.segment_range)

                self._validate_segment_range()

                self.segment_instance.save()
                context.kwargs["segment"] = self.segment_instance

        # Make sure the segment relationships are in the correct state
        self.span.check_and_fix_relationships()

        # Refresh self.segment_instance from the db
        self.segment_instance.refresh_from_db()

        # Adjust adjacent segments if not allowing segment gaps for this span
        if not self.span.get_config_dict().get("allow_segment_gaps"):
            print(
                f"About to call adjust_adjacent_segments with {self.segment_instance=} which has "
                f"{self.segment_instance.previous=} and {self.segment_instance.next=}"
            )
            self._adjust_adjacent_segments()

        # Refresh self.segment_instance from the db
        self.segment_instance.refresh_from_db()

        # print(
        #     f"Returning {self.segment_instance=} with "
        #     f"{self.segment_instance.previous=} and {self.segment_instance.next=}"
        # )
        return self.segment_instance

    def _adjust_adjacent_segments(self):
        """Adjust the adjacent segments if not allowing segment gaps."""

        prev_segment = self.segment_instance.previous
        next_segment = self.segment_instance.next

        print(f"Checking adjacent segments for {self.segment_instance=} with {prev_segment=} and {next_segment=}")
        print(f"Number of segments in span: {len(self.span.get_active_segments())}")
        if prev_segment:
            print(
                f"BEFORE Compared to previous: {prev_segment.segment_range.upper=} "
                f"{self.segment_instance.segment_range.lower=}"
            )
        if next_segment:
            print(
                f"BEFORE Compared to next: {next_segment.segment_range.lower=} "
                f"{self.segment_instance.segment_range.upper=}"
            )

        if prev_segment and prev_segment.segment_range.upper != self.segment_instance.segment_range.lower:
            with SegmentUpdateSignalContext(prev_segment):
                print(f"Setting upper boundary of {prev_segment=} to {self.segment_instance.segment_range.lower=}")
                prev_segment.set_upper_boundary(self.segment_instance.segment_range.lower)
                prev_segment.save()

        if next_segment and next_segment.segment_range.lower != self.segment_instance.segment_range.upper:
            with SegmentUpdateSignalContext(next_segment):
                print(f"Setting lower boundary of {next_segment=} to {self.segment_instance.segment_range.upper=}")
                next_segment.set_lower_boundary(self.segment_instance.segment_range.upper)
                next_segment.save()

        if prev_segment:
            print(
                f"AFTER Compared to previous: {prev_segment.segment_range.upper=} "
                f"{self.segment_instance.segment_range.lower=}"
            )
        if next_segment:
            print(
                f"AFTER Compared to next: {next_segment.segment_range.lower=} "
                f"{self.segment_instance.segment_range.upper=}"
            )

    def _validate_segment_range(self):
        """Validate the segment range based on the span and any adjacent segments."""
        if (
            self.segment_range.lower < self.span.current_range.lower
            or self.segment_range.upper > self.span.current_range.upper
        ):
            raise ValueError("Segment range must be within the span's current range.")


class SegmentHelperBase(BaseHelper):
    """Base class for segment helpers.

    Cannot be used directly.
    """

    def __new__(cls, *args, **kwargs):
        """Ensure that only children of this class are instantiated."""
        if cls is SegmentHelperBase:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    def __init__(self, obj: AbstractSegment):
        super().__init__(obj)
        self.config_dict = SegmentConfigurationHelper().get_config_dict(obj)

    def validate_segment_range(self, *, segment_range: Union[Range, DateRange, DateTimeTZRange, NumericRange]):
        """Validate the segment range based on the span and any adjacent segments."""
        if segment_range.lower < self.obj.segment_range.lower or segment_range.upper > self.obj.segment_range.upper:
            raise ValueError("Segment range must be within the span's current range.")

    def get_annotated_segments(self):
        """Get all segments for the span annotated with additional information."""
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


class ShiftSegmentHelper(SegmentHelperBase):
    """Helper class for shifting an entire segment.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = ShiftSegmentHelper(segment)
        helper.shift_by_value(delta_value=10)
    """

    @transaction.atomic
    def shift_by_value(self, *, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the range value of the entire Segment."""
        self.validate_delta_value_type(delta_value)

        with SpanUpdateSignalContext(self.obj.span):
            # Adjust the lower and upper boundary by the provided value
            with SegmentUpdateSignalContext(self.obj):
                self.obj.set_boundaries(
                    self.obj.segment_range.lower + delta_value, self.obj.segment_range.upper + delta_value
                )
                self.obj.save()


class ShiftLowerSegmentHelper(SegmentHelperBase):
    """Helper class for shifting just the lower boundary of a segment.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = ShiftLowerSegmentHelper(segment)
        helper.shift_lower_by_value(delta_value=10)

        # Alternatively, you can shift the lower boundary to a specific value:
        helper.shift_lower_to_value(to_value=10)
    """

    @transaction.atomic
    def shift_lower_by_value(self, *, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the lower boundary of the Segment's segment_range by the given delta_value."""
        self.validate_delta_value_type(delta_value)
        new_lower = self.obj.segment_range.lower + delta_value

        self.shift_lower_to_value(to_value=new_lower)

    @transaction.atomic
    def shift_lower_to_value(self, *, to_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the lower boundary of the Segment's segment_range to the given value."""
        # Validate the value type
        self.validate_value_type(to_value)

        # Make sure the to_value is less than the upper boundary
        if to_value >= self.obj.segment_range.upper:
            raise ValueError("New lower boundary must be less than the current upper boundary.")

        print(f"Shifting lower boundary from {self.obj.segment_range.lower} to {to_value}")

        with SpanUpdateSignalContext(self.obj.span):
            # If to_value is less than the span's lower boundary, extend the span
            if to_value < self.obj.span.current_range.lower:
                ExtendSpanHelper(self.obj.span).extend_to(value=to_value)
            # Shift the lower boundary to the new value
            with SegmentUpdateSignalContext(self.obj):
                self.obj.segment_range = self.set_boundary(
                    range_field=self.obj.segment_range, new_boundary=to_value, boundary_type=BoundaryType.LOWER
                )
                self.obj.save()


class ShiftUpperSegmentHelper(SegmentHelperBase):
    """Helper class for shifting the upper boundary of a segment.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = ShiftUpperSegmentHelper(segment)
        helper.shift_upper_by_value(delta_value=10)

        # Alternatively, you can shift the upper boundary to a specific value:
        helper.shift_upper_to_value(to_value=10)
    """

    @transaction.atomic
    def shift_upper_by_value(self, *, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the upper boundary of the Segment's segment_range by the given delta_value."""
        self.validate_delta_value_type(delta_value)
        to_value = self.obj.segment_range.upper + delta_value

        self.shift_upper_to_value(to_value=to_value)

    @transaction.atomic
    def shift_upper_to_value(self, *, to_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the upper boundary of the Segment's segment_range to the given value."""
        # Validate the value type
        self.validate_value_type(to_value)

        # Make sure the  is greater than the lower boundary
        if to_value <= self.obj.segment_range.lower:
            raise ValueError("New upper boundary must be greater than the current lower boundary.")

        print(f"Shifting upper boundary from {self.obj.segment_range.upper} to {to_value}")

        with SpanUpdateSignalContext(self.obj.span):
            # If to_value is greater than the span's upper boundary, extend the span
            if to_value > self.obj.span.current_range.upper:
                ExtendSpanHelper(self.obj.span).extend_to(value=to_value)
            # Shift the upper boundary to the new value
            with SegmentUpdateSignalContext(self.obj):
                self.obj.segment_range = self.set_boundary(
                    range_field=self.obj.segment_range, new_boundary=to_value, boundary_type=BoundaryType.UPPER
                )
                self.obj.save()


class SplitSegmentHelper(SegmentHelperBase):
    """Helper class for splitting segments.

    Splitting a segment creates a new segment with the provided split value as the lower boundary.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = SplitSegmentHelper(segment)
        new_segment = helper.split(
            split_value=10,
            fields_to_copy=["field1", "field2"],
        )
    """

    @transaction.atomic
    def split(
        self, *, split_value: Union[int, Decimal, timezone.timedelta], fields_to_copy: Optional[List[str]] = None
    ) -> AbstractSegment:
        """Split the segment into two at the provided split value."""
        self.validate_value_type(split_value)

        RangeClass = self.range_type  # pylint: disable=C0103
        print(f"{RangeClass=} {type(RangeClass)=}")

        with SpanUpdateSignalContext(self.obj.span):
            # Update the provided segment with its new upper boundary (split value)
            with SegmentUpdateSignalContext(self.obj):
                self.obj.set_upper_boundary(split_value)
                self.obj.save()

            # Create a new segment with the split value as the lower boundary
            with SegmentCreateSignalContext(
                span=self.obj.span,
                segment_range=RangeClass(
                    lower=split_value,
                    upper=self.obj.segment_range.upper,
                ),
            ) as context:
                new_segment_data = {field: getattr(self.obj, field, None) for field in fields_to_copy or []}

                upper_segment_range = RangeClass(lower=split_value, upper=self.obj.segment_range.upper)
                new_segment = CreateSegmentHelper(
                    span=self.obj.span, segment_range=upper_segment_range, **new_segment_data
                ).create()
                context.kwargs["segment"] = new_segment

        return new_segment


class MergeSegmentHelper(SegmentHelperBase):
    """Helper class for merging segments.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = MergeSegmentHelper(segment)
        helper.merge_into_upper()

        # Alternatively, you can merge the segment into the previous segment:
        helper.merge_into_lower()
    """

    @transaction.atomic
    def merge_into_upper(self):
        """Merge the current segment into the next (upper) segment."""
        next_segment = self.obj.next

        if not next_segment:
            raise ValueError("No next segment to merge into.")

        with SpanUpdateSignalContext(self.obj.span):
            # Merge the current segment into the next one (removing the next segment)
            with SegmentUpdateSignalContext(self.obj):
                self.obj.set_upper_boundary(next_segment.segment_range.upper)

                if self.config_dict["soft_delete"]:
                    with SegmentSoftDeleteSignalContext(next_segment):
                        next_segment.deleted_at = timezone.now()
                        next_segment.save()
                else:
                    with SegmentDeleteSignalContext(next_segment):
                        next_segment.delete()

                self.obj.save()

    @transaction.atomic
    def merge_into_lower(self):
        """Merge the current segment into the previous (lower) segment."""
        previous_segment = self.obj.previous

        if not previous_segment:
            raise ValueError("No previous segment to merge into.")

        # Merge the current segment into the previous one (removing the current segment)
        with SpanUpdateSignalContext(self.obj.span):
            with SegmentUpdateSignalContext(previous_segment):
                previous_segment.set_upper_boundary(self.obj.segment_range.upper)

                if self.config_dict["soft_delete"]:
                    with SegmentSoftDeleteSignalContext(self.obj):
                        self.obj.deleted_at = timezone.now()
                        self.obj.save()
                else:
                    with SegmentDeleteSignalContext(self.obj):
                        self.obj.delete()

                previous_segment.save()


class DeleteSegmentHelper(SegmentHelperBase):
    """Helper class for deleting segments.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = DeleteSegmentHelper(segment)
        helper.soft_delete()
    """

    @transaction.atomic
    def soft_delete(self):
        """Soft delete the Segment."""

        # Soft delete: mark the Segment as deleted
        current_time = timezone.now()

        with SegmentSoftDeleteSignalContext(self.obj):
            self.obj.deleted_at = current_time
            self.obj.save()


class InsertSegmentHelper(SegmentHelperBase):
    """Helper class for inserting segments.

    Usage:

    .. code-block:: python

        segment = MySegment.objects.get(id=1)
        helper = InsertSegmentHelper(segment)
        new_segment = helper.insert(span=span, segment_range=segment_range)
    """

    @transaction.atomic
    def insert(self, *, span: AbstractSpan, segment_range: Union[Range, DateRange, DateTimeTZRange, NumericRange]):
        """Insert a new segment into the span."""  # ToDo: This should be similar to split, ind include the fields_to_copy
        self.validate_segment_range(segment_range=segment_range)

        with SpanUpdateSignalContext(span):
            with SegmentCreateSignalContext(span=span, segment_range=segment_range) as context:
                new_segment = CreateSegmentHelper(span=span, segment_range=segment_range).create()
                context.kwargs["segment"] = new_segment

        return new_segment
