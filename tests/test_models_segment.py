import pytest
from django.db import transaction
from django.db.models import F
from psycopg2.extras import NumericRange

from django_segments.models.segment import AbstractSegment
from tests.example.models import ConcreteIntegerSegment
from tests.factories import RANGE_DELTA_VALUE


@pytest.mark.django_db
class TestSegment:
    """Tests for the segment model."""

    def test_segment_creation(self, integer_segment):
        """Test creation of an integer segment."""
        segment = integer_segment
        assert segment is not None
        assert isinstance(segment, AbstractSegment)
        assert segment.segment_range.lower == 0
        assert segment.segment_range.upper == RANGE_DELTA_VALUE

    def test_segment_lower_boundary_shift(self, integer_segment):
        """Test shifting the lower boundary of a segment."""
        segment = integer_segment
        old_lower_boundary = segment.segment_range.lower
        segment.shift_lower_by_value(delta_value=2)
        segment.refresh_from_db()

        assert segment.segment_range.lower == old_lower_boundary + 2

    def test_segment_upper_boundary_shift(self, integer_segment):
        """Test shifting the upper boundary of a segment."""
        segment = integer_segment
        old_upper_boundary = segment.segment_range.upper
        segment.shift_upper_by_value(delta_value=2)
        segment.refresh_from_db()

        assert segment.segment_range.upper == old_upper_boundary + 2

    def test_segment_shift_by_value(self, integer_segment):
        """Test shifting both boundaries of a segment."""
        segment = integer_segment
        old_lower_boundary = segment.segment_range.lower
        old_upper_boundary = segment.segment_range.upper
        shift_value = 2

        segment.shift_by_value(delta_value=shift_value)
        segment.refresh_from_db()

        assert segment.segment_range.lower == old_lower_boundary + shift_value
        assert segment.segment_range.upper == old_upper_boundary + shift_value

    def test_segment_soft_delete(self, integer_segment):
        """Test soft deletion of a segment."""
        segment = integer_segment
        segment.delete()
        segment.refresh_from_db()

        assert segment.deleted_at is not None

    def test_segment_hard_delete(self, integer_segment):
        """Test hard deletion of a segment."""
        segment = integer_segment
        # segment.get_config_dict().update({"soft_delete": False})
        segment.SegmentConfig.soft_delete = False
        segment.delete()

        print(f"{segment=} {segment.deleted_at=}")
        with pytest.raises(ConcreteIntegerSegment.DoesNotExist):
            segment.refresh_from_db()

    def test_segment_boundary_conditions(self, integer_span_and_segments):
        """Test that segment boundaries are maintained correctly."""
        span, segments = integer_span_and_segments  # pylint: disable=W0612
        segment1, segment2, segment3 = segments  # pylint: disable=W0612

        # Trying to set the lower boundary of the third segment to be less than the first segment's upper boundary
        with pytest.raises(ValueError):
            segment3.set_lower_boundary(segment1.segment_range.upper - 1)

        # Trying to set the upper boundary of the first segment to be more than the third segment's lower boundary
        with pytest.raises(ValueError):
            segment1.set_upper_boundary(segment3.segment_range.lower + 1)

    def test_segment_split(self, integer_segment):
        """Test splitting a segment."""
        segment = integer_segment
        old_upper_boundary = segment.segment_range.upper
        split_value = segment.segment_range.lower + 2

        new_segment = segment.split(split_value=split_value)
        new_segment.refresh_from_db()

        assert segment.segment_range.upper == split_value
        assert new_segment.segment_range.lower == split_value
        assert new_segment.segment_range.upper == old_upper_boundary

    @pytest.mark.django_db(transaction=True)
    def test_segment_transaction(self, integer_segment):
        """Ensure atomic transactions when shifting boundaries."""
        segment = integer_segment
        lower_segment = segment
        upper_segment = integer_segment

        with pytest.raises(ValueError):
            with transaction.atomic():
                lower_segment.shift_upper_to_value(to_value=1)
                upper_segment.shift_lower_to_value(to_value=2)

        lower_segment.refresh_from_db()
        upper_segment.refresh_from_db()

        assert lower_segment.segment_range.upper != upper_segment.segment_range.lower

    def test_append_segment(self, integer_span):
        """Test appending a new segment to a span."""
        span = integer_span
        value = span.current_range.upper + RANGE_DELTA_VALUE

        new_segment = span.append(to_value=value)
        new_segment.refresh_from_db()

        assert new_segment.segment_range.lower == span.current_range.upper
        assert new_segment.segment_range.upper == value


@pytest.mark.django_db
class TestSegmentAdditional:
    """Additional tests for segment model."""

    def test_merge_into_upper(self, integer_span_and_segments):
        """Test merging a segment into the next upper segment."""
        span, segments = integer_span_and_segments
        _, segment2, segment3 = segments

        old_upper_value = segment3.segment_range.upper
        segment2.merge_into_upper()
        span.refresh_from_db()

        # Ensure that merging adjusts the upper boundary correctly
        assert segment2.segment_range.upper == old_upper_value
        assert not span.segments.filter(id=segment3.id).exists()

    def test_merge_into_lower(self, integer_span_and_segments):
        """Test merging a segment into the previous lower segment."""
        span, segments = integer_span_and_segments
        segment1, segment2, _ = segments

        old_lower_value = segment1.segment_range.lower
        segment2.merge_into_lower()
        span.refresh_from_db()

        # Ensure that merging adjusts the lower boundary correctly
        assert segment2.segment_range.lower == old_lower_value
        assert not span.segments.filter(id=segment1.id).exists()

    def test_insert_segment(self, integer_span):
        """Test inserting a new segment into an existing span."""
        span = integer_span
        new_range = NumericRange(3, 7)
        segment = span.get_segment_class().objects.create(span=span, segment_range=new_range)
        span.refresh_from_db()

        assert segment in span.get_segments()
        # Check segment boundaries
        assert segment.segment_range == new_range
        assert segment.segment_range.lower == 3
        assert segment.segment_range.upper == 7

    def test_is_first_and_last_property(self, integer_segment):
        """Test is_first_and_last property for a single segment."""
        segment = integer_segment
        assert segment.is_first_and_last

    def test_is_internal_property(self, datetime_span_and_segments):
        """Test is_internal property for internal segments."""
        _, segments = datetime_span_and_segments
        segment1, segment2, segment3 = segments

        assert not segment1.is_internal
        assert segment2.is_internal
        assert not segment3.is_internal

    def test_boundary_cross_validation(self, integer_span_and_segments):
        """Test validation of boundaries across adjacent segments."""
        _, segments = integer_span_and_segments
        segment1, segment2, _ = segments

        # Swap boundaries to check validation
        with pytest.raises(ValueError) as excinfo:
            segment1.set_upper_boundary(segment2.segment_range.lower - 1)
        assert "Boundary crossing detected" in str(excinfo.value)

    def test_delete_transitions(self, datetime_span_and_segments):
        """Test transitions for soft deleting segments."""
        _, segments = datetime_span_and_segments
        segment1, segment2, _ = segments

        segment1.delete()
        segment2.refresh_from_db()

        # Ensure state transitions are handled
        assert segment1.deleted_at is not None
        assert segment2.previous_segment is None

    def test_get_next_segment(self, integer_span_and_segments):
        """Test retrieving the next segment of a segment."""
        _, segments = integer_span_and_segments
        segment1, segment2, segment3 = segments

        assert segment1.next == segment2
        assert segment2.next == segment3
        assert segment3.next is None

    def test_get_previous_segment(self, integer_span_and_segments):
        """Test retrieving the previous segment of a segment."""
        _, segments = integer_span_and_segments
        segment1, segment2, segment3 = segments

        assert segment3.previous == segment2
        assert segment2.previous == segment1
        assert segment1.previous is None

    def test_get_first_segment(self, datetime_span_and_segments):
        """Test retrieving the first segment of a span."""
        span, segments = datetime_span_and_segments
        first_segment = span.first_segment

        assert first_segment == segments[0]
        assert not first_segment.previous

    def test_get_last_segment(self, datetime_span_and_segments):
        """Test retrieving the last segment of a span."""
        span, segments = datetime_span_and_segments
        last_segment = span.last_segment

        assert last_segment == segments[-1]
        assert not last_segment.next

    def test_split_segment(self, integer_segment):
        """Test splitting a segment correctly."""
        segment = integer_segment
        split_value = segment.segment_range.lower + 2

        new_segment = segment.split(split_value=split_value)
        segment.refresh_from_db()
        new_segment.refresh_from_db()

        assert segment.segment_range.upper == split_value
        assert new_segment.segment_range.lower == split_value
        assert new_segment.previous_segment == segment
        assert segment.next_segment == new_segment
