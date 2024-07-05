"""Basic tests to make sure our fixtures are working."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from tests.factories import RANGE_DELTA_VALUE


@pytest.mark.django_db
class TestFixtureCreation:
    """Test that the fixtures are created."""

    def test_big_integer_segment(self, big_integer_segment):
        """Test that a big integer segment can be created."""
        assert big_integer_segment is not None

    def test_big_integer_span(self, big_integer_span):
        """Test that a big integer span can be created."""
        assert big_integer_span is not None

    def test_date_segment(self, date_segment):
        """Test that a date segment can be created."""
        assert date_segment is not None

    def test_date_span(self, date_span):
        """Test that a date span can be created."""
        assert date_span is not None

    def test_datetime_segment(self, datetime_segment):
        """Test that a datetime segment can be created."""
        assert datetime_segment is not None

    def test_datetime_span(self, datetime_span):
        """Test that a datetime span can be created."""
        assert datetime_span is not None

    def test_decimal_segment(self, decimal_segment):
        """Test that a decimal segment can be created."""
        assert decimal_segment is not None

    def test_decimal_span(self, decimal_span):
        """Test that a decimal span can be created."""
        assert decimal_span is not None

    def test_integer_segment(self, integer_segment):
        """Test that an integer segment can be created."""
        assert integer_segment is not None

    def test_integer_span(self, integer_span):
        """Test that an integer span can be created."""
        assert integer_span is not None

    def test_integer_span_and_segments(self, integer_span_and_segments):
        """Test that an integer span with multiple segments can be created."""
        assert integer_span_and_segments is not None

    def test_big_integer_span_and_segments(self, big_integer_span_and_segments):
        """Test that a big integer span with multiple segments can be created."""
        assert big_integer_span_and_segments is not None

    def test_date_span_and_segments(self, date_span_and_segments):
        """Test that a date span with multiple segments can be created."""
        assert date_span_and_segments is not None

    def test_datetime_span_and_segments(self, datetime_span_and_segments):
        """Test that a datetime span with multiple segments can be created."""
        assert datetime_span_and_segments is not None

    def test_decimal_span_and_segments(self, decimal_span_and_segments):
        """Test that a decimal span with multiple segments can be created."""
        assert decimal_span_and_segments is not None


@pytest.mark.django_db
class TestSettingFixtureValues:
    """Test that the values of the fixtures are set correctly."""

    def test_integer_span_creation(self, integer_span):
        """Test that an integer span can be created."""
        assert integer_span.initial_range.lower == 0
        assert integer_span.initial_range.upper == RANGE_DELTA_VALUE
        assert integer_span.current_range.lower == integer_span.initial_range.lower
        assert integer_span.current_range.upper == integer_span.initial_range.upper

    def test_integer_span_and_segments_creation(self, integer_span_and_segments):
        """Test that an integer span with multiple segments can be created."""
        _, segments = integer_span_and_segments
        assert len(segments) == 3
        segment1, segment2, segment3 = segments

        assert segment1.segment_range.upper == segment2.segment_range.lower
        assert segment1.segment_range.upper - segment1.segment_range.lower == RANGE_DELTA_VALUE
        assert segment2.segment_range.upper - segment2.segment_range.lower == RANGE_DELTA_VALUE
        assert segment3.segment_range.upper - segment3.segment_range.lower == RANGE_DELTA_VALUE

    def test_big_integer_span_creation(self, big_integer_span):
        """Test that a big integer span can be created."""
        assert big_integer_span.initial_range.lower == 0
        assert big_integer_span.initial_range.upper == RANGE_DELTA_VALUE
        assert big_integer_span.current_range.lower == big_integer_span.initial_range.lower
        assert big_integer_span.current_range.upper == big_integer_span.initial_range.upper

    def test_big_integer_span_and_segments_creation(self, big_integer_span_and_segments):
        """Test that a big integer span with multiple segments can be created."""
        _, segments = big_integer_span_and_segments
        assert len(segments) == 3
        segment1, segment2, segment3 = segments

        assert segment1.segment_range.upper == segment2.segment_range.lower
        assert segment1.segment_range.upper - segment1.segment_range.lower == RANGE_DELTA_VALUE
        assert segment2.segment_range.upper - segment2.segment_range.lower == RANGE_DELTA_VALUE
        assert segment3.segment_range.upper - segment3.segment_range.lower == RANGE_DELTA_VALUE

    def test_decimal_span_creation(self, decimal_span):
        """Test that a decimal span can be created."""
        assert decimal_span.initial_range.lower == Decimal("0.0")
        assert decimal_span.initial_range.upper == Decimal(f"{RANGE_DELTA_VALUE}.0")
        assert decimal_span.current_range.lower == decimal_span.initial_range.lower
        assert decimal_span.current_range.upper == decimal_span.initial_range.upper

    def test_decimal_span_and_segments_creation(self, decimal_span_and_segments):
        """Test that a decimal span with multiple segments can be created."""
        _, segments = decimal_span_and_segments
        assert len(segments) == 3
        segment1, segment2, segment3 = segments

        assert segment1.segment_range.upper == segment2.segment_range.lower
        assert segment1.segment_range.upper - segment1.segment_range.lower == Decimal(f"{RANGE_DELTA_VALUE}.0")
        assert segment2.segment_range.upper - segment2.segment_range.lower == Decimal(f"{RANGE_DELTA_VALUE}.0")
        assert segment3.segment_range.upper - segment3.segment_range.lower == Decimal(f"{RANGE_DELTA_VALUE}.0")

    def test_date_span_creation(self, date_span):
        """Test that a date span can be created."""
        assert date_span.initial_range.lower < date_span.initial_range.upper
        assert date_span.current_range.lower == date_span.initial_range.lower
        assert date_span.current_range.upper == date_span.initial_range.upper

    def test_date_span_and_segments_creation(self, date_span_and_segments):
        """Test that a date span with multiple segments can be created."""
        _, segments = date_span_and_segments
        assert len(segments) == 3
        segment1, segment2, segment3 = segments

        assert segment1.segment_range.upper == segment2.segment_range.lower
        assert segment1.segment_range.upper - segment1.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)
        assert segment2.segment_range.upper - segment2.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)
        assert segment3.segment_range.upper - segment3.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)

    def test_datetime_span_creation(self, datetime_span):
        """Test that a datetime span can be created."""
        assert datetime_span.initial_range.lower < datetime_span.initial_range.upper
        assert datetime_span.current_range.lower == datetime_span.initial_range.lower
        assert datetime_span.current_range.upper == datetime_span.initial_range.upper

    def test_datetime_span_and_segments_creation(self, datetime_span_and_segments):
        """Test that a datetime span with multiple segments can be created."""
        _, segments = datetime_span_and_segments
        assert len(segments) == 3
        segment1, segment2, segment3 = segments

        assert segment1.segment_range.upper == segment2.segment_range.lower
        assert segment1.segment_range.upper - segment1.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)
        assert segment2.segment_range.upper - segment2.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)
        assert segment3.segment_range.upper - segment3.segment_range.lower == timedelta(days=RANGE_DELTA_VALUE)
