"""Tests for the Segment helpers."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.postgres.fields import (
    DateRangeField,
    DateTimeRangeField,
    IntegerRangeField,
)
from django.core.exceptions import ValidationError
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)
from django.db.models.base import ModelState
from django.utils import timezone

from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.helpers.base import BaseHelper
from django_segments.helpers.segment import (
    CreateSegmentHelper,
    DeleteSegmentHelper,
    InsertSegmentHelper,
    MergeSegmentHelper,
    ShiftLowerSegmentHelper,
    ShiftSegmentHelper,
    ShiftUpperSegmentHelper,
    SplitSegmentHelper,
)
from django_segments.models import AbstractSegment, AbstractSpan
from tests.example.models import (
    ConcreteBigIntegerSegment,
    ConcreteDateSegment,
    ConcreteDateTimeSegment,
    ConcreteDecimalSegment,
    ConcreteIntegerSegment,
)


@pytest.mark.django_db
class TestCreateSegmentHelper:
    """Tests for the CreateSegmentHelper class."""

    def test_create_segment_without_overlap(self, integer_span):
        """Test creating a segment without overlapping existing segments."""
        segment_range = NumericRange(10, 20)
        helper = CreateSegmentHelper(span=integer_span, segment_range=segment_range)
        segment = helper.create()
        assert segment.segment_range == segment_range

    def test_create_segment_with_overlap_raises_error(self, integer_segment):
        """Test creating a segment with overlapping existing segments should raise an error."""
        segment_range = (Decimal(0), Decimal(5))
        integer_segment.segment_range = segment_range
        helper = CreateSegmentHelper(span=integer_segment.span, segment_range=segment_range)
        with pytest.raises(
            ValueError, match=r"Cannot create segment: proposed range overlaps with the following existing segment\(s\)"
        ):
            helper.create()

    def test_adjust_adjacent_segments_for_upper_gap(self, integer_span_and_segments):
        """Test creation with adjustment of adjacent segments when gaps are not allowed.

        If gaps are not allowed and we create a new segment that would leave a gap between the new segment and the
        adjacent segments, the adjacent segment's range should be adjusted to fill the gap.
        """
        integer_span, [*_, segment3] = integer_span_and_segments  # pylint: disable=W0612
        integer_span.SpanConfig.allow_segment_gaps = False
        helper = CreateSegmentHelper(
            span=integer_span,
            segment_range=NumericRange(integer_span.current_range.upper + 2, integer_span.current_range.upper + 4),
        )
        segment = helper.create()
        # Check that the last initial segment's upper boundary is adjusted to the new segment's lower boundary
        segment3.refresh_from_db()
        assert segment3.segment_range.upper == segment.segment_range.lower

    def test_adjust_adjacent_segments_for_lower_gap(self, integer_span_and_segments):
        """Test creation with adjustment of adjacent segments when gaps are not allowed.

        If gaps are not allowed and we create a new segment that would leave a gap between the new segment and the
        adjacent segments, the adjacent segment's range should be adjusted to fill the gap.
        """
        integer_span, [segment1, *_] = integer_span_and_segments  # pylint: disable=W0612
        integer_span.SpanConfig.allow_segment_gaps = False
        helper = CreateSegmentHelper(
            span=integer_span,
            segment_range=NumericRange(integer_span.current_range.lower - 4, integer_span.current_range.lower - 2),
        )
        segment = helper.create()
        # Check that the first initial segment's lower boundary is adjusted to the new segment's upper boundary
        segment1.refresh_from_db()
        assert segment1.segment_range.lower == segment.segment_range.upper


@pytest.mark.django_db
class TestShiftSegmentHelper:
    """Tests for the ShiftSegmentHelper class."""

    def test_shift_by_value(self, integer_segment):
        """Test shifting the segment range by a positive value."""
        initial_segment_range = integer_segment.segment_range
        helper = ShiftSegmentHelper(integer_segment)
        shift_value = 2
        helper.shift_by_value(delta_value=shift_value)
        assert integer_segment.segment_range == NumericRange(
            initial_segment_range.lower + shift_value, initial_segment_range.upper + shift_value
        )

    def test_shift_segment_below_span_range(self, integer_segment):
        """Test shifting the segment range below the span's range causes the span's range to be adjusted."""
        span_initial_range = integer_segment.span.initial_range
        assert span_initial_range == integer_segment.segment_range

        helper = ShiftSegmentHelper(integer_segment)
        shift_value = -(integer_segment.span.current_range.upper - integer_segment.span.current_range.lower) + 1
        helper.shift_by_value(delta_value=shift_value)

        assert integer_segment.span.current_range == integer_segment.segment_range

    def test_shift_segment_above_span_range(self, integer_segment):
        """Test shifting the segment range above the span's range causes the span's range to be adjusted."""
        span_initial_range = integer_segment.span.initial_range
        assert span_initial_range == integer_segment.segment_range

        helper = ShiftSegmentHelper(integer_segment)
        shift_value = (integer_segment.span.current_range.upper - integer_segment.span.current_range.lower) + 1
        helper.shift_by_value(delta_value=shift_value)

        assert integer_segment.span.current_range == integer_segment.segment_range


@pytest.mark.django_db
class TestShiftByValueDifferentTypes:
    """Tests for the `shift_by_value` method with different value types."""

    @pytest.mark.parametrize(
        "segment, helper_class, value",
        [
            ("integer_segment", ShiftSegmentHelper, 5),
            ("big_integer_segment", ShiftSegmentHelper, 5),
            ("decimal_segment", ShiftSegmentHelper, Decimal("5.5")),
            ("date_segment", ShiftSegmentHelper, timedelta(days=5)),
            ("datetime_segment", ShiftSegmentHelper, timedelta(days=5)),
        ],
    )
    def test_shift_by_value_different_types(self, segment, helper_class, value, request):
        """Test shifting the segment range by a value of different types."""
        segment_instance = request.getfixturevalue(segment)
        helper = helper_class(segment_instance)
        helper.shift_by_value(delta_value=value)
        assert segment_instance.segment_range.lower + value == helper.obj.segment_range.lower
        assert segment_instance.segment_range.upper + value == helper.obj.segment_range.upper


@pytest.mark.django_db
class TestShiftLowerSegmentHelper:
    """Tests for the ShiftLowerSegmentHelper class."""

    def test_shift_lower_boundary_by_positive_value(self, integer_segment):
        """Test shifting the lower segment range by a positive value."""
        shift_value = 2
        original_segment_lower = integer_segment.segment_range.lower

        helper = ShiftLowerSegmentHelper(integer_segment)
        helper.shift_lower_by_value(delta_value=shift_value)
        assert integer_segment.segment_range.lower != integer_segment.segment_range.upper
        assert integer_segment.segment_range.lower == (original_segment_lower + shift_value)
        assert integer_segment.segment_range.lower >= integer_segment.span.current_range.lower

    def test_shift_lower_boundary_by_negative_value(self, integer_segment):
        """Test shifting the lower segment range by a negative value."""
        shift_value = -2
        original_segment_lower = integer_segment.segment_range.lower

        helper = ShiftLowerSegmentHelper(integer_segment)
        helper.shift_lower_by_value(delta_value=shift_value)
        assert integer_segment.segment_range.lower != integer_segment.segment_range.upper
        assert integer_segment.segment_range.lower == (original_segment_lower + shift_value)
        assert integer_segment.segment_range.lower >= integer_segment.span.current_range.lower

    def test_shift_lower_boundary_to_higher_value(self, integer_segment):
        """Test shifting the lower segment range to a new, higher value."""
        helper = ShiftLowerSegmentHelper(integer_segment)
        new_lower_value = integer_segment.segment_range.lower + 3
        helper.shift_lower_to_value(to_value=new_lower_value)
        assert integer_segment.segment_range.lower == new_lower_value
        assert integer_segment.segment_range.lower >= integer_segment.span.current_range.lower

    def test_shift_lower_boundary_to_lower_value(self, integer_segment):
        """Test shifting the lower segment range to a new, lower value."""
        helper = ShiftLowerSegmentHelper(integer_segment)
        new_lower_value = integer_segment.segment_range.lower - 3
        helper.shift_lower_to_value(to_value=new_lower_value)
        assert integer_segment.segment_range.lower == new_lower_value
        assert integer_segment.segment_range.lower >= integer_segment.span.current_range.lower

    def test_shift_lower_boundary_to_upper_boundary(self, integer_segment):
        """Test shifting the lower segment range to the current upper boundary."""
        helper = ShiftLowerSegmentHelper(integer_segment)
        with pytest.raises(ValueError):
            helper.shift_lower_to_value(to_value=integer_segment.segment_range.upper)


@pytest.mark.django_db
class TestShiftUpperSegmentHelper:
    """Tests for the ShiftUpperSegmentHelper class."""

    def test_shift_upper_boundary_by_positive_value(self, integer_segment):
        """Test shifting the upper segment range by a positive value."""
        shift_value = 2
        original_segment_upper = integer_segment.segment_range.upper

        helper = ShiftUpperSegmentHelper(integer_segment)
        helper.shift_upper_by_value(delta_value=shift_value)
        assert integer_segment.segment_range.upper != integer_segment.segment_range.lower
        assert integer_segment.segment_range.upper == (original_segment_upper + shift_value)
        assert integer_segment.segment_range.upper <= integer_segment.span.current_range.upper

    def test_shift_upper_boundary_by_negative_value(self, integer_segment):
        """Test shifting the upper segment range by a negative value."""
        shift_value = -2
        original_segment_upper = integer_segment.segment_range.upper

        helper = ShiftUpperSegmentHelper(integer_segment)
        helper.shift_upper_by_value(delta_value=shift_value)
        assert integer_segment.segment_range.upper != integer_segment.segment_range.lower
        assert integer_segment.segment_range.upper == (original_segment_upper + shift_value)
        assert integer_segment.segment_range.upper <= integer_segment.span.current_range.upper

    def test_shift_upper_boundary_to_higher_value(self, integer_segment):
        """Test shifting the upper segment range to a new, higher value."""
        helper = ShiftUpperSegmentHelper(integer_segment)
        new_upper_value = integer_segment.segment_range.upper + 3
        helper.shift_upper_to_value(to_value=new_upper_value)
        assert integer_segment.segment_range.upper == new_upper_value
        assert integer_segment.segment_range.upper <= integer_segment.span.current_range.upper

    def test_shift_upper_boundary_to_lower_value(self, integer_segment):
        """Test shifting the upper segment range to a new, lower value."""
        helper = ShiftUpperSegmentHelper(integer_segment)
        new_upper_value = integer_segment.segment_range.upper - 3
        helper.shift_upper_to_value(to_value=new_upper_value)
        assert integer_segment.segment_range.upper == new_upper_value
        assert integer_segment.segment_range.upper <= integer_segment.span.current_range.upper

    def test_shift_upper_boundary_to_lower_boundary(self, integer_segment):
        """Test shifting the upper segment range to the current lower boundary."""
        helper = ShiftUpperSegmentHelper(integer_segment)
        with pytest.raises(ValueError):
            helper.shift_upper_to_value(to_value=integer_segment.segment_range.lower)


@pytest.mark.django_db
class TestSplitSegmentHelper:
    """Tests for the SplitSegmentHelper class."""

    def test_split_segment(self, integer_segment):
        """Test splitting the segment into two at a specific value."""
        helper = SplitSegmentHelper(integer_segment)
        split_value = integer_segment.segment_range.lower + 2
        new_segment = helper.split(split_value=split_value)
        assert new_segment.segment_range.lower == split_value
        assert new_segment.span == integer_segment.span

    def test_split_segment_at_upper_boundary(self, integer_segment):
        """Test splitting the segment exactly at the upper boundary."""
        helper = SplitSegmentHelper(integer_segment)
        with pytest.raises(ValueError):
            helper.split(split_value=integer_segment.segment_range.upper)


@pytest.mark.django_db
class TestDeleteSegmentHelper:
    """Tests for the DeleteSegmentHelper class."""

    def test_soft_delete(self, integer_segment):
        """Test soft deleting a segment."""
        helper = DeleteSegmentHelper(integer_segment)
        helper.soft_delete()
        assert integer_segment.deleted_at is not None

    def test_soft_delete_undelete_segment(self, integer_segment):
        """Test un-deleting a segment that was previously soft deleted."""
        helper = DeleteSegmentHelper(integer_segment)
        helper.soft_delete()
        integer_segment.deleted_at = None
        integer_segment.save()
        assert integer_segment.deleted_at is None


@pytest.mark.django_db
class TestInsertSegmentHelper:
    """Tests for the InsertSegmentHelper class."""

    def test_insert_segment(self, integer_span):
        """Test inserting a segment into the span."""
        segment_range = NumericRange(15, 20)
        helper = InsertSegmentHelper(integer_span)
        new_segment = helper.insert(span=integer_span, segment_range=segment_range)
        assert new_segment.segment_range == segment_range

    def test_insert_overlapping_segment(self, integer_span_and_segments):
        """Test inserting an overlapping segment should raise an error."""
        integer_span, segments = integer_span_and_segments
        helper = InsertSegmentHelper(integer_span)
        with pytest.raises(ValueError, match="overlapping segments are not allowed"):
            helper.insert(span=integer_span, segment_range=segments[1].segment_range)


@pytest.mark.django_db
class TestMergeSegmentHelper:
    """Tests for the MergeSegmentHelper class."""

    def test_merge_into_upper(self, integer_span_and_segments):
        """Test merging a segment into the next (upper) segment."""
        _, [segment1, segment2, segment3] = integer_span_and_segments
        helper = MergeSegmentHelper(segment1)
        helper.merge_into_upper()

        segment1.refresh_from_db()
        segment2.refresh_from_db()
        segment3.refresh_from_db()
        # assert segment2.deleted_at is not None
        assert segment1.segment_range.upper == segment3.segment_range.lower

    def test_merge_into_lower(self, integer_span_and_segments):
        """Test merging a segment into the previous (lower) segment."""
        _, [segment1, segment2, segment3] = integer_span_and_segments
        helper = MergeSegmentHelper(segment3)
        helper.merge_into_lower()

        segment1.refresh_from_db()
        segment2.refresh_from_db()
        segment3.refresh_from_db()
        # assert segment2.deleted_at is not None
        assert segment1.segment_range.upper == segment3.segment_range.lower

    def test_merge_into_upper_without_next_segment(self, integer_segment):
        """Test attempting to merge into upper segment when next segment does not exist."""
        helper = MergeSegmentHelper(integer_segment)
        with pytest.raises(ValueError, match="No next segment to merge into."):
            helper.merge_into_upper()

    def test_merge_into_lower_without_previous_segment(self, integer_segment):
        """Test attempting to merge into lower segment when previous segment does not exist."""
        helper = MergeSegmentHelper(integer_segment)
        with pytest.raises(ValueError, match="No previous segment to merge into."):
            helper.merge_into_lower()

    def test_merge_with_soft_delete(self, integer_span_and_segments):
        """Test merging segments with soft delete enabled."""
        integer_span, [segment1, segment2, segment3] = integer_span_and_segments
        integer_span.SpanConfig.soft_delete = True
        helper = MergeSegmentHelper(segment2)
        helper.merge_into_upper()
        assert segment3.deleted_at is not None
        assert segment1.segment_range.upper == segment3.segment_range.lower
