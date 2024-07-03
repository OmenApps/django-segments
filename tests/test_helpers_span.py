"""Tests for the Span helpers."""

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
from django_segments.helpers.segment import CreateSegmentHelper
from django_segments.helpers.span import (
    AppendSegmentToSpanHelper,
    CreateSpanHelper,
    DeleteSpanHelper,
    ShiftLowerSpanHelper,
    ShiftSpanHelper,
    ShiftUpperSpanHelper,
    SpanHelperBase,
)
from django_segments.models import AbstractSegment, AbstractSpan
from django_segments.signals import span_post_update, span_pre_update
from tests.example.models import (
    ConcreteBigIntegerSegment,
    ConcreteDateSegment,
    ConcreteDateTimeSegment,
    ConcreteDecimalSegment,
    ConcreteIntegerSegment,
)
from tests.factories import RANGE_DELTA_VALUE


@pytest.mark.django_db
class TestCreateSpanHelper:
    """Tests for the CreateSpanHelper class."""

    def test_create_span(self, integer_span):
        """Test that a span can be created."""
        new_span_helper = CreateSpanHelper(model_class=integer_span.__class__)
        range_value = NumericRange(0, 10)
        new_span = new_span_helper.create(range_value=range_value)

        assert new_span.initial_range == range_value
        assert new_span.current_range == range_value

    def test_create_initial_segment(self, integer_span):
        """Test that a segment can be created when creating a span."""
        new_span_helper = CreateSpanHelper(model_class=integer_span.__class__)
        range_value = NumericRange(0, 10)
        new_span = new_span_helper.create(range_value=range_value)

        CreateSegmentHelper(span=new_span, segment_range=range_value).create()

        assert new_span.get_segments().first() is not None
        segment = new_span.first_segment
        assert segment is not None
        assert segment.segment_range == range_value

    def test_create_span_with_custom_range(self, decimal_span):
        """Test that a span can be created with a custom range."""
        new_span_helper = CreateSpanHelper(model_class=decimal_span.__class__)
        range_value = NumericRange(Decimal("0.0"), Decimal("15.0"))
        new_span = new_span_helper.create(range_value=range_value)

        assert new_span.initial_range == range_value
        assert new_span.current_range == range_value

    def test_create_span_with_gaps(self, big_integer_span):
        """Test that a span can be created with gaps."""
        new_span_helper = CreateSpanHelper(model_class=big_integer_span.__class__)
        range_value = NumericRange(0, 20)
        new_span = new_span_helper.create(range_value=range_value)

        segment_count = new_span.get_segments().count()
        assert segment_count == 0  # Expecting zero segments since gaps are allowed

    def test_create_span_without_gaps(self, integer_span):
        """Test that a span can be created without gaps."""
        integer_span.SpanConfig.allow_span_gaps = False
        new_span_helper = CreateSpanHelper(model_class=integer_span.__class__)
        range_value = NumericRange(0, 10)
        new_span = new_span_helper.create(range_value=range_value)

        segment = new_span.get_segments().first()
        assert segment.segment_range == range_value
        assert new_span.current_range == range_value

        # Set allow_span_gaps back to True
        integer_span.SpanConfig.allow_span_gaps = True


@pytest.mark.django_db
class TestShiftSpanHelper:
    """Tests for the ShiftSpanHelper class."""

    # @pytest.mark.parametrize(
    #     "shift_value, expected_range",
    #     [(1, NumericRange(1, 11)), (-1, NumericRange(-1, 9)), (Decimal("1.5"), NumericRange(1.5, 11.5))],
    # )
    # def test_shift_by_value_integer(self, integer_span_and_segments, shift_value, expected_range):
    #     """Test that the span can be shifted by a value."""
    #     span, segments = integer_span_and_segments
    #     shift_helper = ShiftSpanHelper(span)
    #     shift_helper.shift_by_value(value=shift_value)

    #     span.refresh_from_db()
    #     assert span.current_range == expected_range

    # @pytest.mark.parametrize(
    #     "shift_value, expected_range",
    #     [
    #         (
    #             timedelta(days=1),
    #             DateRange(timezone.now().date() + timedelta(days=1), timezone.now().date() + timedelta(days=11)),
    #         ),
    #         (
    #             -timedelta(days=1),
    #             DateRange(timezone.now().date() + timedelta(days=-1), timezone.now().date() + timedelta(days=9)),
    #         ),
    #         (
    #             timedelta(hours=12),
    #             DateRange(
    #                 timezone.now().date() + timedelta(hours=12), timezone.now().date() + timedelta(days=10, hours=12)
    #             ),
    #         ),
    #     ],
    # )
    # def test_shift_by_value_date(self, date_span_and_segments, shift_value, expected_range):
    #     """Test that the span can be shifted by a value."""
    #     span, segments = date_span_and_segments
    #     shift_helper = ShiftSpanHelper(span)
    #     shift_helper.shift_by_value(value=shift_value)

    #     span.refresh_from_db()
    #     assert span.current_range == expected_range

    # @pytest.mark.parametrize("shift_value", [(1), (-1), (Decimal("1.5")), (-Decimal("1.5"))])
    # def test_shift_by_value_with_signals(self, integer_span_and_segments, shift_value):
    #     """Test that the span can be shifted by a value with signals."""
    #     span, segments = integer_span_and_segments
    #     shift_helper = ShiftSpanHelper(span)

    #     pre_update_called, post_update_called = False, False

    #     def pre_update(sender, **kwargs):
    #         nonlocal pre_update_called
    #         pre_update_called = True

    #     def post_update(sender, **kwargs):
    #         nonlocal post_update_called
    #         post_update_called = True

    #     span_pre_update.connect(pre_update, sender=span.__class__)
    #     span_post_update.connect(post_update, sender=span.__class__)

    #     shift_helper.shift_by_value(value=shift_value)

    #     span.refresh_from_db()
    #     assert pre_update_called
    #     assert post_update_called

    #     span_pre_update.disconnect(pre_update, sender=span.__class__)
    #     span_post_update.disconnect(post_update, sender=span.__class__)

    def test_shift_by_value_decimal_range(self, decimal_span_and_segments):
        """Test that the span can be shifted by a value."""
        span, _ = decimal_span_and_segments
        shift_helper = ShiftSpanHelper(span)
        shift_helper.shift_by_value(value=Decimal("1.0"))

        span.refresh_from_db()
        assert span.current_range == NumericRange(Decimal("1.0"), Decimal("5.0"))

    # def test_shift_by_value_date_range(self, date_span_and_segments):
    #     """Test that the span can be shifted by a value."""
    #     span, segments = date_span_and_segments
    #     shift_helper = ShiftSpanHelper(span)
    #     shift_value = timedelta(days=1)
    #     shift_helper.shift_by_value(value=shift_value)

    #     span.refresh_from_db()
    #     assert span.current_range == DateRange(
    #         span.initial_range.lower + shift_value, span.initial_range.upper + shift_value
    #     )


# @pytest.mark.django_db
# class TestShiftLowerSpanHelper:
#     """Tests for the ShiftLowerSpanHelper class."""
#     def test_shift_lower_by_value_integer(self, integer_span_and_segments):
#         """Test that the lower boundary of the span can be shifted by a value."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_by_value(value=1)

#         span.refresh_from_db()
#         assert span.current_range.lower == 1

#     def test_shift_lower_by_value_date(self, date_span_and_segments):
#         """Test that the lower boundary of the span can be shifted by a value."""
#         span, segments = date_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_by_value(value=timedelta(days=1))

#         span.refresh_from_db()
#         assert span.current_range.lower == timezone.now().date() + timedelta(days=1)

#     def test_shift_lower_by_value_invalid(self, integer_span_and_segments):
#         """Test that an invalid lower boundary shift raises an error."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         with pytest.raises(
#             ValueError,
#             match="The new lower boundary cannot be greater than or equal to the lowest segment's lower boundary.",
#         ):
#             shift_helper.shift_lower_by_value(value=6)

#     def test_shift_lower_by_value_decimal(self, decimal_span_and_segments):
#         """Test that the lower boundary of the span can be shifted by a value."""
#         span, segments = decimal_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_by_value(value=Decimal("1.0"))

#         span.refresh_from_db()
#         assert span.current_range.lower == Decimal("1.0")

#     def test_shift_lower_by_value_edge_case(self, integer_span_and_segments):
#         """Test that an edge case lower boundary shift raises an error."""
#         span, segments = integer_span_and_segments
#         segments[0].set_lower_boundary(3)
#         segments[0].save()
#         shift_helper = ShiftLowerSpanHelper(span)

#         with pytest.raises(ValueError):
#             shift_helper.shift_lower_by_value(5)


# @pytest.mark.django_db
# class TestShiftUpperSpanHelper:
#     """Tests for the ShiftUpperSpanHelper class."""
#     def test_shift_upper_by_value_integer(self, integer_span_and_segments):
#         """Test that the upper boundary of the span can be shifted by a value."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_by_value(value=1)

#         span.refresh_from_db()
#         assert span.current_range.upper == 11

#     def test_shift_upper_by_value_date(self, date_span_and_segments):
#         """Test that the upper boundary of the span can be shifted by a value."""
#         span, segments = date_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_by_value(value=timedelta(days=1))

#         span.refresh_from_db()
#         assert span.current_range.upper == timezone.now().date() + timedelta(days=11)

#     def test_shift_upper_by_value_invalid(self, integer_span_and_segments):
#         """Test that an invalid upper boundary shift raises an error."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         with pytest.raises(
#             ValueError,
#             match="The new upper boundary cannot be less than or equal to the highest segment's upper boundary.",
#         ):
#             shift_helper.shift_upper_by_value(value=-1)

#     def test_shift_upper_by_value_decimal(self, decimal_span_and_segments):
#         """Test that the upper boundary of the span can be shifted by a value."""
#         span, segments = decimal_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_by_value(value=Decimal("1.0"))

#         span.refresh_from_db()
#         assert span.current_range.upper == Decimal("11.0")

#     def test_shift_upper_by_max_upper_date(self, datetime_span_and_segments):
#         """Test that the upper boundary of the span can be shifted by a value."""
#         span, segments = datetime_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_by_value(value=timedelta(days=1))

#         span.refresh_from_db()
#         assert span.current_range.upper == span.initial_range.upper + timedelta(days=1)


# @pytest.mark.django_db
# class TestShiftLowerSpanHelper:
#     """Tests for the ShiftLowerSpanHelper class."""
#     def test_shift_lower_to_value_integer(self, integer_span_and_segments):
#         """Test that the lower boundary of the span can be shifted to a value."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_to_value(new_value=5)

#         span.refresh_from_db()
#         assert span.current_range.lower == 5

#     def test_shift_lower_to_value_date(self, date_span_and_segments):
#         """Test that the lower boundary of the span can be shifted to a value."""
#         span, segments = date_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         new_value = timezone.now().date() + timedelta(days=3)
#         shift_helper.shift_lower_to_value(new_value=new_value)

#         span.refresh_from_db()
#         assert span.current_range.lower == new_value

#     def test_shift_lower_to_value_decimal(self, decimal_span_and_segments):
#         """Test that the lower boundary of the span can be shifted to a value."""
#         span, segments = decimal_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_to_value(new_value=Decimal("2.0"))

#         span.refresh_from_db()
#         assert span.current_range.lower == Decimal("2.0")

#     def test_shift_lower_to_value_boundaries(self, integer_span_and_segments):
#         """Test that the lower boundary of the span can be shifted to a value."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftLowerSpanHelper(span)
#         shift_helper.shift_lower_to_value(new_value=4)

#         span.refresh_from_db()
#         assert span.current_range.lower == 4


# @pytest.mark.django_db
# class TestShiftUpperSpanHelper:
#     """Tests for the ShiftUpperSpanHelper class."""
#     def test_shift_upper_to_value_integer(self, integer_span_and_segments):
#         """Test that the upper boundary of the span can be shifted to a value."""
#         span, segments = integer_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_to_value(new_value=15)

#         span.refresh_from_db()
#         assert span.current_range.upper == 15

#     def test_shift_upper_to_value_date(self, date_span_and_segments):
#         """Test that the upper boundary of the span can be shifted to a value."""
#         span, segments = date_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         new_value = timezone.now().date() + timedelta(days=15)
#         shift_helper.shift_upper_to_value(new_value=new_value)

#         span.refresh_from_db()
#         assert span.current_range.upper == new_value

#     def test_shift_upper_to_value_decimal(self, decimal_span_and_segments):
#         """Test that the upper boundary of the span can be shifted to a value."""
#         span, segments = decimal_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_to_value(new_value=Decimal("15.0"))

#         span.refresh_from_db()
#         assert span.current_range.upper == Decimal("15.0")

#     def test_shift_upper_to_value_timedate(self, datetime_span_and_segments):
#         """Test that the upper boundary of the span can be shifted to a value."""
#         span, segments = datetime_span_and_segments
#         shift_helper = ShiftUpperSpanHelper(span)
#         shift_helper.shift_upper_to_value(new_value=timezone.now() + timedelta(days=15))

#         span.refresh_from_db()
#         assert span.current_range.upper == timezone.now() + timedelta(days=15)


# @pytest.mark.django_db
# class TestAppendSegmentToSpanHelper:
#     """Tests for appending a Segment to a Span."""
#     def test_append_integer(self, integer_span_and_segments):
#         """Test that a segment can be appended to a span."""
#         span, segments = integer_span_and_segments
#         append_helper = AppendSegmentToSpanHelper(span)
#         append_helper.append(value=NumericRange(10, 15))

#         span.refresh_from_db()
#         new_segment = span.get_segments().latest("segment_range__upper")
#         assert new_segment.segment_range == NumericRange(10, 15)
#         assert span.current_range.upper == 15

#     def test_append_date(self, date_span_and_segments):
#         """Test that a segment can be appended to a span."""
#         span, segments = date_span_and_segments
#         append_helper = AppendSegmentToSpanHelper(span)
#         append_helper.append(
#             value=DateRange((timezone.now() + timedelta(days=10)).date(), (timezone.now() + timedelta(days=15)).date())
#         )

#         span.refresh_from_db()
#         new_segment = span.get_segments().latest("segment_range__upper")
#         assert new_segment.segment_range == DateRange(
#             (timezone.now() + timedelta(days=10)).date(), (timezone.now() + timedelta(days=15)).date()
#         )
#         assert span.current_range.upper == (timezone.now() + timedelta(days=15)).date()

#     def test_append_with_existing(self, integer_span_and_segments):
#         """Test that a segment can be appended to a span with existing segments."""
#         span, segments = integer_span_and_segments
#         append_helper = AppendSegmentToSpanHelper(span)
#         new_segment = append_helper.append(value=NumericRange(10, 15))

#         assert new_segment.previous_segment == segments[-1]
#         assert new_segment.segment_range == NumericRange(10, 15)

#     def test_append_with_gap(self, big_integer_span_and_segments):
#         """Test that a segment can be appended to a span with a gap."""
#         span, segments = big_integer_span_and_segments
#         append_helper = AppendSegmentToSpanHelper(span)
#         new_segment = append_helper.append(value=NumericRange(10, 15))

#         assert new_segment.previous_segment is None
#         assert new_segment.segment_range == NumericRange(10, 15)


@pytest.mark.django_db
class TestDeleteSpanHelper:
    """Tests for deleting a Span."""

    # def test_delete_integer(self, integer_span_and_segments):
    #     """Test that the span can be deleted."""
    #     span, segments = integer_span_and_segments
    #     delete_helper = DeleteSpanHelper(span)
    #     delete_helper.delete()

    #     with pytest.raises(AbstractSpan.DoesNotExist):
    #         AbstractSpan.objects.get(id=span.id)

    def test_soft_delete_integer(self, integer_span_and_segments):
        """Test that the span can be soft deleted."""
        span, segments = integer_span_and_segments
        span_class = span.__class__
        span_class.SpanConfig.soft_delete = True
        delete_helper = DeleteSpanHelper(span)
        delete_helper.delete()

        span.refresh_from_db()
        assert span.deleted_at is not None
        assert all(segment.deleted_at is not None for segment in span.get_segments())

    # def test_hard_delete_integer(self, integer_span_and_segments):
    #     """Test that the span can be hard deleted."""
    #     span, segments = integer_span_and_segments
    #     span_class = span.__class__
    #     span_class.SpanConfig.soft_delete = False
    #     delete_helper = DeleteSpanHelper(span)
    #     delete_helper.delete()

    #     with pytest.raises(AbstractSpan.DoesNotExist):
    #         AbstractSpan.objects.get(id=span.id)
    #     assert not span.get_segments().exists()

    # def test_soft_delete_flag(self, date_span_and_segments):
    #     """Test that the soft delete flag is respected."""
    #     span, segments = date_span_and_segments
    #     delete_helper = DeleteSpanHelper(span)
    #     delete_helper.delete()

    #     span.refresh_from_db()
    #     assert span.deleted_at is not None
    #     for segment in segments:
    #         assert segment.deleted_at is not None

    # def test_hard_delete_no_gaps(self, integer_span):
    #     """Test that the span can be hard deleted."""
    #     IntegerSpan = integer_span.__class__
    #     IntegerSpan.SpanConfig.soft_delete = False

    #     span = integer_span
    #     append_helper = AppendSegmentToSpanHelper(span)
    #     segment1 = append_helper.append(value=NumericRange(0, RANGE_DELTA_VALUE))
    #     segment2 = append_helper.append(value=NumericRange(RANGE_DELTA_VALUE, RANGE_DELTA_VALUE * 2))

    #     delete_helper = DeleteSpanHelper(span)
    #     delete_helper.delete()

    #     with pytest.raises(AbstractSpan.DoesNotExist):
    #         AbstractSpan.objects.get(id=span.id)

    #     assert not span.get_segments().exists()  # No segment should exist
