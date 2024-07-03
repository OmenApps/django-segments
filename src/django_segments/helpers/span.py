"""Helper classes for working with spans.

These classes are used to create, update, and delete spans.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union

from django.db import transaction
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
from django_segments.exceptions import SegmentRelationshipError
from django_segments.helpers.base import BaseHelper, BoundaryType
from django_segments.models.base import SpanConfigurationHelper


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django_segments.models import AbstractSpan


class SpanHelperBase(BaseHelper):  # pylint: disable=R0903
    """Base class for span helpers."""

    def __new__(cls, *args, **kwargs):
        """Ensure that only children of this class are instantiated."""
        if cls is SpanHelperBase:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    def __init__(self, obj: AbstractSpan):
        super().__init__(obj)
        self.config_dict = SpanConfigurationHelper.get_config_dict(obj)


class CreateSpanHelper:
    """Helper class for creating spans.

    Any additional keyword arguments are passed to the span's create method.

    Does not inherit from BaseHelper because there is initially no object to work with.
    """

    def __init__(self, model_class: type[AbstractSpan]):
        self.model_class = model_class
        self.config_dict = SpanConfigurationHelper.get_config_dict(model_class)

    @transaction.atomic
    def create(self, *, range_value: Range = None, **kwargs):
        """Create a new Span instance with initial_range and current_range fields set.

        Optionally create an initial Segment that spans the entire range if needed.
        """
        if range_value is None:
            raise ValueError("range_value must be provided")

        # Initialize range values in kwargs
        kwargs.update({"initial_range": range_value, "current_range": range_value})

        # Create the Span instance
        with SpanCreateSignalContext(span_model=self.model_class, span_range=range_value) as context:
            span_instance = self.model_class.objects.create(**kwargs)
            context.kwargs["span"] = span_instance

        # Create an initial Segment of the same length as the span if not allowed to have gaps
        if not self.config_dict.get("allow_span_gaps", True):
            self.create_initial_segment(span_instance)

        return span_instance

    def create_initial_segment(self, span_instance: AbstractSpan):
        """Create an initial Segment that spans the entire range of the Span."""
        segment_class = span_instance.get_segment_class()
        print(f"Creating initial segment of {segment_class=} for {span_instance=}")
        segment_range = span_instance.current_range

        with SegmentCreateSignalContext(segment_class) as context:
            segment = segment_class.objects.create(span=span_instance, segment_range=segment_range)
            context.kwargs["segment"] = segment

        return segment


class ExtendSpanHelper(SpanHelperBase):
    """Helper class for extending a span's boundaries to encompass a value (or range of values).

    Usage:

    .. code-block:: python

        span = ConcreteIntegerSpan.objects.create(initial_range=NumericRange(0, 4), current_range=NumericRange(0, 4))
        helper = ExtendSpanHelper(span)
        helper.extend_to_value(10)

        # Alternate, with a range
        helper.extend_to_value(NumericRange(0, 10))
    """

    @transaction.atomic
    def extend_to_value(self, value: Union[int, Decimal, timezone.timedelta, Range]):
        """Extend the current_range of the Span to include the given value, which may be a single value or a range.

        Args:
            value (int, Decimal, datetime.timedelta): The value to include in the current_range.
        """
        # Validate the value type
        if isinstance(value, Range):
            self.validate_value_type(value.lower)
            self.validate_value_type(value.upper)
        else:
            self.validate_value_type(value)

        # Extend the current_range of the Span
        with SpanUpdateSignalContext(self.obj):
            self.obj.current_range = self.get_extended_range(self.obj.current_range, value)
            self.obj.save()

    def get_extended_range(self, range_field: Range, value: Union[int, Decimal, timezone.timedelta, Range]) -> Range:
        """Extend the given range field to include the specified value.

        Args:
            range_field (Range): The range field to extend.
            value (int, Decimal, datetime.timedelta): The value to include in the range.

        Returns:
            Range: The extended range.
        """
        if isinstance(value, Range):
            return range_field.__class__(
                lower=min(range_field.lower, value.lower),
                upper=max(range_field.upper, value.upper),
            )

        return range_field.__class__(
            lower=min(range_field.lower, value),
            upper=max(range_field.upper, value),
        )


class ShiftSpanHelper(SpanHelperBase):
    """Helper class for shifting spans."""

    @transaction.atomic
    def shift_by_value(self, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the entire range value of the Span and each of its associated Segments by the given delta_value.

        Args:
            delta_value (int, Decimal, datetime.timedelta): The value by which to shift the range.
        """
        # Validate the delta_value type
        self.validate_value_type(delta_value)

        # Shift the current_range of the Span
        with SpanUpdateSignalContext(self.obj):
            self.obj.current_range = self.get_shifted_range(self.obj.current_range, delta_value)

            # Get all segments and shift their ranges
            segments = self.obj.get_segments()
            for segment in segments:
                with SegmentUpdateSignalContext(segment) as segment_context:
                    segment.segment_range = self.get_shifted_range(segment.segment_range, delta_value)
                    segment.save()
                    segment_context.kwargs["segment"] = segment

            self.obj.save()

    def get_shifted_range(self, range_field: Range, delta_value: Union[int, Decimal, timezone.timedelta]) -> Range:
        """Shift the given range field by the specified delta_value.

        Args:
            range_field (Range): The range field to shift.
            delta_value (int, Decimal, datetime.timedelta): The value by which to shift the range.

        Returns:
            Range: The shifted range.
        """
        return range_field.__class__(
            lower=range_field.lower + delta_value,
            upper=range_field.upper + delta_value,
        )


class ShiftSpanBoundaryHelperBase(SpanHelperBase):  # pylint: disable=R0903
    """Base class for shifting the boundaries of a span."""

    def _check_for_gap(self, new_boundary, boundary_type: BoundaryType):
        """Check if the shift would cause a gap between the span boundary and the segments.

        If gaps are not allowed, shift the segment boundary to the new span boundary.
        """
        if not self.config_dict.get("allow_span_gaps", True):
            segment = self._get_segment(boundary_type)
            if (boundary_type == BoundaryType.LOWER and segment.segment_range.lower > new_boundary) or (
                boundary_type == BoundaryType.UPPER and segment.segment_range.upper < new_boundary
            ):
                with SegmentUpdateSignalContext(segment) as segment_context:
                    self._set_segment_boundary(segment, new_boundary, boundary_type)
                    segment.save()
                    segment_context.kwargs["segment"] = segment

    def _delete_or_soft_delete_external_segments(self, new_boundary, boundary_type: BoundaryType):
        """Delete or soft delete segments that would be completely outside the span."""
        segments = self.obj.get_segments()
        for segment in segments:
            if (boundary_type == BoundaryType.LOWER and segment.segment_range.upper < new_boundary) or (
                boundary_type == BoundaryType.UPPER and segment.segment_range.lower > new_boundary
            ):
                if self.config_dict.get("soft_delete", True):
                    with SegmentSoftDeleteSignalContext(segment) as segment_context:
                        segment.deleted_at = timezone.now()
                        segment.save()
                        segment_context.kwargs["segment"] = segment
                else:
                    with SegmentDeleteSignalContext(segment) as segment_context:
                        segment.delete()
                        segment_context.kwargs["segment"] = segment

    def _shift_external_segment_boundaries(self, new_boundary, boundary_type: BoundaryType):
        """Shift the boundaries of segments that would extend beyond the span."""
        segments = self.obj.get_segments()
        for segment in segments:
            if (boundary_type == BoundaryType.LOWER and segment.segment_range.lower < new_boundary) or (
                boundary_type == BoundaryType.UPPER and segment.segment_range.upper > new_boundary
            ):
                with SegmentUpdateSignalContext(segment) as segment_context:
                    self._set_segment_boundary(segment, new_boundary, boundary_type)
                    segment.save()
                    segment_context.kwargs["segment"] = segment

    def _get_segment(self, boundary_type: BoundaryType):
        """Get the relevant segment based on the boundary type."""
        return self.obj.first_segment if boundary_type == BoundaryType.LOWER else self.obj.last_segment

    def _set_segment_boundary(self, segment, new_boundary, boundary_type: BoundaryType):
        """Set the segment boundary based on the boundary type."""
        if boundary_type == BoundaryType.LOWER:
            segment.set_lower_boundary(new_boundary)
        else:
            segment.set_upper_boundary(new_boundary)


class ShiftLowerSpanHelper(ShiftSpanBoundaryHelperBase):
    """Helper class for shifting the lower boundary of a span."""

    @transaction.atomic
    def shift_lower_by_value(self, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the lower boundary of the Span's current_range by the given delta_value.

        Args:
            delta_value (int, Decimal, timedelta): The value by which to shift the lower boundary.
        """
        new_lower = self.calculate_new_boundary(self.obj.current_range.lower, delta_value)

        self.validate_value_type(new_lower)
        self.validate_range(self.obj.current_range, new_lower, self.obj.current_range.upper)

        with SpanUpdateSignalContext(self.obj):
            self.obj.current_range = self.set_boundary(self.obj.current_range, new_lower, BoundaryType.LOWER)

            self._delete_or_soft_delete_external_segments(new_lower, BoundaryType.LOWER)
            self._check_for_gap(new_lower, BoundaryType.LOWER)
            self._shift_external_segment_boundaries(new_lower, BoundaryType.LOWER)

            self.obj.save()

    @transaction.atomic
    def shift_lower_to_value(self, to_value: Union[int, Decimal, datetime, date]):
        """Shift the lower boundary of the Span's current_range to the given value.

        Args:
            to_value (int, Decimal, datetime, or date): The new value for the lower boundary.
        """
        self.validate_value_type(to_value)
        delta_value = to_value - self.obj.current_range.lower
        self.shift_lower_by_value(delta_value)


class ShiftUpperSpanHelper(ShiftSpanBoundaryHelperBase):
    """Helper class for shifting the upper boundary of a span."""

    @transaction.atomic
    def shift_upper_by_value(self, delta_value: Union[int, Decimal, timezone.timedelta]):
        """Shift the upper boundary of the Span's current_range by the given value.

        Args:
            delta_value (int, Decimal, timedelta): The value by which to shift the upper boundary.
        """
        new_upper = self.calculate_new_boundary(self.obj.current_range.upper, delta_value)

        self.validate_value_type(new_upper)
        self.validate_range(self.obj.current_range, new_upper, self.obj.current_range.lower)

        with SpanUpdateSignalContext(self.obj):
            self.obj.current_range = self.set_boundary(self.obj.current_range, new_upper, BoundaryType.UPPER)

            self._delete_or_soft_delete_external_segments(new_upper, BoundaryType.UPPER)
            self._check_for_gap(new_upper, BoundaryType.UPPER)
            self._shift_external_segment_boundaries(new_upper, BoundaryType.UPPER)

            self.obj.save()

    @transaction.atomic
    def shift_upper_to_value(self, to_value: Union[int, Decimal, datetime, date]):
        """Shift the upper boundary of the Span's current_range to the given value.

        Args:
            to_value (int, Decimal, datetime, or date): The new value for the upper boundary.
        """
        self.validate_value_type(to_value)
        delta_value = to_value - self.obj.current_range.upper
        self.shift_upper_by_value(delta_value)


class AppendSegmentToSpanHelper(SpanHelperBase):  # pylint: disable=R0903
    """Helper class for appending a segment to the current span."""

    @transaction.atomic
    def append(
        self,
        to_value: Optional[Union[int, Decimal, date, datetime]] = None,
        delta_value: Optional[Union[int, Decimal, timezone.timedelta]] = None,
        **kwargs,
    ):
        """Append a segment with either the specified upper value or an upper value calculated from the delta value.

        Only one of `value` or `delta_value` should be provided.

        Any additional keyword arguments are passed to the segment's create method.
        """
        self._validate_input(to_value, delta_value)

        if delta_value is not None:
            to_value = self._calculate_value_from_delta(delta_value)

        self.validate_value_type(to_value)
        self._validate_value_against_boundaries(to_value)

        # Get the last segment to use as the new segment's previous segment
        last_segment = self.obj.last_segment

        # Get the segment class to use when creating the new segment
        segment_class = self.obj.get_segment_class()

        with SpanUpdateSignalContext(self.obj):
            self._extend_span_to_value(to_value)

            with SegmentCreateSignalContext(segment_class) as context:
                segment = self._create_segment(segment_class, last_segment, to_value, **kwargs)
                context.kwargs["segment"] = segment

        return segment

    def _validate_input(self, to_value, delta_value):
        """Validate that one and only one of to_value or delta_value is provided."""
        if (to_value is None and delta_value is None) or (to_value is not None and delta_value is not None):
            raise ValueError("One and only one of to_value or delta_value must be provided.")

    def _calculate_value_from_delta(self, delta_value):
        """Calculate the value if delta_value is provided."""
        return self.obj.current_range.upper + delta_value

    def _validate_to_value_against_boundaries(self, to_value):
        """Validate the to_value compared to the current upper boundary and the last segment's upper boundary."""
        if to_value <= self.obj.current_range.upper and to_value <= self.obj.last_segment.segment_range.upper:
            raise ValueError(
                "The to_value must be greater than the current upper boundary or the last segment's upper boundary."
            )

    def _extend_span_to_value(self, to_value):
        """Extend the span's current range to include the new value."""
        helper = ExtendSpanHelper(self.obj)
        helper.extend_to_value(to_value)

    def _create_segment(self, segment_class, last_segment, to_value, **kwargs):
        """Create a new segment with the given parameters."""
        return segment_class.objects.create(
            span=self.obj,
            segment_range=self.get_appended_segment_range(last_segment, to_value),
            previous_segment=last_segment,
            **kwargs,
        )


class DeleteSpanHelper(SpanHelperBase):  # pylint: disable=R0903
    """Helper class for deleting spans."""

    @transaction.atomic
    def delete(self):
        """Delete the Span and its associated Segments.

        Handles soft deletes by marking the Span and its Segments as deleted.
        Handles hard deletes by performing a hard delete of the Span and its Segments.
        """
        segments = self.obj.get_segments()

        if self.config_dict.get("soft_delete", True):
            # Soft delete: mark the Span and its Segments as deleted
            current_time = timezone.now()

            with SpanSoftDeleteSignalContext(self.obj):
                self.obj.deleted_at = current_time

                for segment in segments:
                    segment.delete()  # Signals are sent in the delete method, so not needed here

                self.obj.save()
        else:
            # Hard delete: delete the Span and its Segments
            with SpanDeleteSignalContext(self.obj):
                with SegmentDeleteSignalContext(self.obj):
                    segments.delete()

                self.obj.delete()


class RelationshipHelper(SpanHelperBase):  # pylint: disable=R0903
    """Helper class for creating relationships between a span's segments.

    Usage:

    .. code-block:: python

        span = ConcreteIntegerSpan.objects.create(initial_range=NumericRange(0, 4), current_range=NumericRange(0, 4))

        # Check and Fix relationships between the span's segments
        helper = RelationshipHelper(span)
        helper.check_and_fix_relationships()
    """

    def check_and_fix_relationships(self):
        """Check and fix the relationships between the segments in the span."""
        try:
            self._validate_relationships()
        except SegmentRelationshipError:
            self._fix_relationships()

    def _validate_relationships(self):
        """Checks the order of segments, and ensures the `previous_segment` field is set correctly."""
        segments = self.obj.get_active_segments()
        for i, segment in enumerate(segments):
            if i == 0:
                if segment.previous_segment is not None:
                    print(f"Relationships are NOT valid for {self.obj=}")
                    raise SegmentRelationshipError("The first segment in the span should not have a previous segment.")
            else:
                if segment.previous_segment != segments[i - 1]:
                    print(f"Relationships are NOT valid for {self.obj=}")
                    raise SegmentRelationshipError(
                        "The previous_segment field should be set to the previous segment in the span."
                    )

    @transaction.atomic
    def _fix_relationships(self):
        """Fix the relationships between the segments in the span."""

        # First, we remove any relationships for inactive segments
        inactive_segments = self.obj.get_inactive_segments()
        for segment in inactive_segments:
            if segment.previous_segment is not None:
                with SegmentUpdateSignalContext(segment):
                    print(f"Removing relationships for inactive segment {segment}")
                    segment.previous_segment = None
                    segment.save()

            # If any other segment has this segment set as previous_segment, we remove the relationship
            self._remove_as_previous_segment(segment)

        segments = self.obj.get_active_segments()
        print(f"Fixing relationships for {self.obj=} with {segments=}")

        for idx, segment in enumerate(segments):
            # The first segment should not have a previous segment
            print(f"Fixing relationships for {segment=} with {segment.previous=} and {segment.next=}")
            if idx == 0 and segment.previous is not None:
                with SegmentUpdateSignalContext(segment):
                    segment.previous_segment = None
                    segment.save()
                    print(f"Fixed relationships for {segment=} to have {segment.previous=}")
                    return
            # Set the previous_segment field to the previous segment in the span
            elif idx - 1 >= 0 and segment.previous != segments[idx - 1]:
                with SegmentUpdateSignalContext(segment):
                    segment.previous_segment = segments[idx - 1]
                    segment.save()
                    print(f"Fixed relationships for {segment=} to have {segment.previous=}")

    def _remove_as_previous_segment(self, segment):
        """Update previous_segment field to None for any segment that has the given segment as its previous segment."""
        check_segments = self.obj.get_segments()
        for check_segment in check_segments:
            if check_segment.previous == segment:
                with SegmentUpdateSignalContext(check_segment):
                    check_segment.previous_segment = None
                    check_segment.save()
                    print(f"Removed {segment} from previous_segment for {check_segment}")
