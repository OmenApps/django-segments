from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.core.exceptions import ValidationError
from django.utils import timezone
from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange

from tests.example.models import (
    ConcreteBigIntegerSegment,
    ConcreteBigIntegerSpan,
    ConcreteDateSegment,
    ConcreteDateSpan,
    ConcreteDateTimeSegment,
    ConcreteDateTimeSpan,
    ConcreteDecimalSegment,
    ConcreteDecimalSpan,
    ConcreteIntegerSegment,
    ConcreteIntegerSpan,
    EventSegment,
    EventSpan,
)
from tests.factories import RANGE_DELTA_VALUE


@pytest.mark.django_db
class TestCreateSpan:
    """Tests for creating a span instance."""

    def test_create_span(self, integer_span):
        """Verifies span is created correctly with matching initial_range and correct boundaries."""
        assert integer_span.initial_range == integer_span.current_range
        assert integer_span.initial_range.lower == 0
        assert integer_span.initial_range.upper == RANGE_DELTA_VALUE

    def test_create_datetime_span(self, datetime_span):
        """Verifies datetime span is created correctly with matching initial_range and correct boundaries."""
        assert datetime_span.initial_range == datetime_span.current_range
        assert datetime_span.initial_range.lower.date() == timezone.now().date()
        assert datetime_span.initial_range.upper.date() == (timezone.now() + timedelta(days=RANGE_DELTA_VALUE)).date()


@pytest.mark.django_db
class TestShiftSpan:
    """Tests for shifting the span boundaries."""

    def test_shift_by_value(self, integer_span_and_segments):
        """Verifies that the span and segments can be shifted correctly."""
        integer_span, [segment1, segment2, segment3] = integer_span_and_segments
        integer_span.shift_by_value(2)

        assert integer_span.current_range.lower == 2
        assert integer_span.current_range.upper == (RANGE_DELTA_VALUE * 3) + 2
        assert segment1.segment_range.lower == 2
        assert segment1.segment_range.upper == RANGE_DELTA_VALUE + 2
        assert segment2.segment_range.lower == RANGE_DELTA_VALUE + 2
        assert segment2.segment_range.upper == (RANGE_DELTA_VALUE * 2) + 2
        assert segment3.segment_range.lower == (RANGE_DELTA_VALUE * 2) + 2
        assert segment3.segment_range.upper == (RANGE_DELTA_VALUE * 3) + 2

    # def test_shift_lower_by_value(self, integer_span):
    #     """Verifies that the span lower boundary can be shifted correctly."""
    #     integer_span.shift_lower_by_value(-1)
    #     assert integer_span.current_range.lower == -1
    #     assert integer_span.current_range.upper == 10

    # def test_shift_upper_by_value(self, integer_span):
    #     """Verifies that the span upper boundary can be shifted correctly."""
    #     integer_span.shift_upper_by_value(2)
    #     assert integer_span.current_range.lower == 0
    #     assert integer_span.current_range.upper == 12

    # def test_shift_lower_to_value(self, integer_span):
    #     """Verifies that the span lower boundary can be shifted to a specific value."""
    #     integer_span.shift_lower_to_value(1)
    #     assert integer_span.current_range.lower == 1
    #     assert integer_span.current_range.upper == 10

    # def test_shift_upper_to_value(self, integer_span):
    #     """Verifies that the span upper boundary can be shifted to a specific value."""
    #     integer_span.shift_upper_to_value(9)
    #     assert integer_span.current_range.lower == 0
    #     assert integer_span.current_range.upper == 9

    # def test_shift_edges(self, decimal_span_and_segments):
    #     """Verifies that the span boundaries can be shifted to the limits."""
    #     span, segments = decimal_span_and_segments
    #     span.shift_lower_to_value(Decimal("0.0"))
    #     span.shift_upper_to_value(Decimal("10.0"))
    #     assert span.current_range.lower == Decimal("0.0")
    #     assert span.current_range.upper == Decimal("10.0")

    # @pytest.mark.parametrize(
    #     "span_fixture,range_field_type,value",
    #     [
    #         ("integer_span", NumericRange, RANGE_DELTA_VALUE),
    #         ("big_integer_span", NumericRange, RANGE_DELTA_VALUE),
    #         ("decimal_span", NumericRange, Decimal("5.0")),  # ToDo: FIX
    #         ("date_span", DateRange, timezone.now().date() + timedelta(days=RANGE_DELTA_VALUE)),
    #         ("datetime_span", DateTimeTZRange, timezone.now() + timedelta(days=RANGE_DELTA_VALUE)),
    #     ],
    # )
    # def test_shift_span_by_value(self, span_fixture, range_field_type, value, request):
    #     """Test that the span can be shifted by a given value."""
    #     span = request.getfixturevalue(span_fixture)
    #     original_range = span.current_range
    #     span.shift_by_value(value)
    #     assert span.current_range.lower == original_range.lower + value
    #     assert span.current_range.upper == original_range.upper + value

    #     # Check that the segments were also shifted
    #     for segment in span.get_segments():
    #         assert segment.segment_range.lower == original_range.lower + value
    #         assert segment.segment_range.upper == original_range.upper + value

    #     # Check range type
    #     assert isinstance(span.current_range, range_field_type)


@pytest.mark.django_db
class TestDeleteSpan:
    """Tests for deleting the span."""

    def test_soft_delete(self, integer_span):
        """Verifies that the span can be soft deleted."""
        integer_span.delete()
        assert integer_span.deleted_at is not None

    # def test_hard_delete(self, mocker, integer_span):
    #     """Verifies that the span can be hard deleted."""
    #     config_mock = mocker.patch(
    #         "tests.example.models.ConcreteIntegerSpan.get_config_dict", return_value={"soft_delete": False}
    #     )
    #     integer_span.delete()
    #     with pytest.raises(ConcreteIntegerSpan.DoesNotExist):
    #         ConcreteIntegerSpan.objects.get(id=integer_span.id)

    # def test_delete_cascade_to_segments(self, datetime_span_and_segments):
    #     """Verifies that deleting a span cascades to the segments."""
    #     span, segments = datetime_span_and_segments
    #     span.delete()
    #     for segment in segments:
    #         assert segment.deleted_at is not None


@pytest.mark.django_db
class TestGetDetails:
    """Tests for getting details about the span."""

    # def test_span_config_dict(self, integer_span):
    #     """Verifies that the span config dict is created correctly."""
    #     config = integer_span.get_config_dict()
    #     assert config["allow_span_gaps"] is True
    #     assert config["allow_segment_gaps"] is True
    #     assert config["soft_delete"] is True

    def test_get_segment_class(self, integer_span):
        """Verifies that the correct segment class is returned for the span."""
        segment_class = integer_span.get_segment_class()
        assert segment_class == ConcreteIntegerSegment


@pytest.mark.django_db
class TestBoundaryMethods:
    """Tests for setting and validating span boundaries."""

    def test_set_initial_boundary(self, integer_span):
        """Verifies that the initial span boundaries can be set correctly."""
        integer_span.set_initial_lower_boundary(1)
        integer_span.set_initial_upper_boundary(9)
        assert integer_span.initial_range.lower == 1
        assert integer_span.initial_range.upper == 9

    def test_set_boundary(self, integer_span):
        """Verifies that the span boundaries can be set correctly."""
        integer_span.set_lower_boundary(1)
        integer_span.set_upper_boundary(9)
        assert integer_span.current_range.lower == 1
        assert integer_span.current_range.upper == 9

    def test_boundary_validation(self, integer_span):
        """Verifies that boundary values are validated correctly."""
        with pytest.raises(ValueError):
            integer_span.set_lower_boundary(None)
        with pytest.raises(ValueError):
            integer_span.set_lower_boundary("invalid_type")

    def test_set_boundary_to_limits(self, decimal_span):
        """Verifies that the span boundaries can be set to the limits."""
        decimal_span.set_lower_boundary(Decimal("0.0"))
        decimal_span.set_upper_boundary(Decimal("10.0"))
        assert decimal_span.current_range.lower == Decimal("0.0")
        assert decimal_span.current_range.upper == Decimal("10.0")


@pytest.mark.django_db
class TestSpanSegments:
    """Tests for getting segments associated with the span."""

    def test_get_segments(self, integer_span_and_segments):
        """Verifies that the segments associated with the span are returned correctly."""
        span, segments = integer_span_and_segments
        assert list(span.get_segments()) == segments

    # def test_get_segments_with_deleted(self, integer_span_and_segments):
    #     """Verifies that the segments associated with the span are returned correctly."""
    #     span, segments = integer_span_and_segments
    #     segments[0].delete()
    #     assert list(span.get_segments(include_deleted=True)) == segments

    # def test_get_segments_with_deleted_excluded(self, integer_span_and_segments):
    #     """Verifies that the segments associated with the span are returned correctly."""
    #     span, segments = integer_span_and_segments
    #     segments[0].delete()
    #     assert list(span.get_segments()) == segments[1:]

    def test_first_segment(self, datetime_span_and_segments):
        """Verifies that the first segment is returned correctly."""
        span, segments = datetime_span_and_segments
        first_segment = span.first_segment
        assert first_segment == segments[0]

    def test_last_segment(self, datetime_span_and_segments):
        """Verifies that the last segment is returned correctly."""
        span, segments = datetime_span_and_segments
        last_segment = span.last_segment
        assert last_segment == segments[-1]
