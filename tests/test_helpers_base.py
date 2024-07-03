"""Tests for the BaseHelper class."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)
from django.utils import timezone

from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.helpers.base import BaseHelper
from tests.example.models import (
    ConcreteBigIntegerSegment,
    ConcreteDateSegment,
    ConcreteDateTimeSegment,
    ConcreteDecimalSegment,
    ConcreteIntegerSegment,
)
from tests.factories import RANGE_DELTA_VALUE


@pytest.mark.parametrize(
    "segment, expected_field_type",
    [
        ("integer_segment", "NumericRange"),
        ("big_integer_segment", "NumericRange"),
        ("decimal_segment", "NumericRange"),
        ("date_segment", "DateRange"),
        ("datetime_segment", "DateTimeTZRange"),
    ],
)
@pytest.mark.django_db
def test_base_helper_initialization(segment, expected_field_type, request):
    """Test that the BaseHelper class can actually be initialized."""
    segment_instance = request.getfixturevalue(segment)
    print(f"{segment_instance=}")
    base_helper = BaseHelper(segment_instance)
    assert base_helper.field_value_type == expected_field_type


@pytest.mark.parametrize(
    "value, is_valid",
    [
        (-RANGE_DELTA_VALUE, True),
        (RANGE_DELTA_VALUE, True),
        (-float(RANGE_DELTA_VALUE), False),
        (float(RANGE_DELTA_VALUE), False),
        (Decimal(f"-{RANGE_DELTA_VALUE}.0"), False),
        (Decimal(f"{RANGE_DELTA_VALUE}.0"), False),
        (timezone.now().date(), False),
        (timezone.now(), False),
        (None, False),
    ],
)
@pytest.mark.django_db
def test_base_helper_validate_integer_value_type(value, is_valid, integer_span):
    """Test that the `validate_value_type` method of the BaseHelper class works as expected for integer fields."""
    segment_range = NumericRange(0, RANGE_DELTA_VALUE)
    segment_instance = ConcreteIntegerSegment.objects.create(span=integer_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)

    if is_valid:
        base_helper.validate_value_type(value)
    else:
        with pytest.raises(ValueError):
            base_helper.validate_value_type(value)


@pytest.mark.parametrize(
    "value, is_valid",
    [
        (-RANGE_DELTA_VALUE, True),
        (RANGE_DELTA_VALUE, True),
        (float(-RANGE_DELTA_VALUE), False),
        (float(RANGE_DELTA_VALUE), False),
        (Decimal(f"-{RANGE_DELTA_VALUE}.0"), False),
        (Decimal(f"{RANGE_DELTA_VALUE}.0"), False),
        (timezone.now().date(), False),
        (timezone.now(), False),
        (None, False),
    ],
)
@pytest.mark.django_db
def test_base_helper_validate_big_integer_value_type(value, is_valid, big_integer_span):
    """Test that the `validate_value_type` method of the BaseHelper class works as expected for big integer fields."""
    segment_range = NumericRange(0, RANGE_DELTA_VALUE)
    segment_instance = ConcreteBigIntegerSegment.objects.create(span=big_integer_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)

    if is_valid:
        base_helper.validate_value_type(value)
    else:
        with pytest.raises(ValueError):
            base_helper.validate_value_type(value)


@pytest.mark.parametrize(
    "value, is_valid",
    [
        (-RANGE_DELTA_VALUE, False),
        (RANGE_DELTA_VALUE, False),
        (float(-RANGE_DELTA_VALUE), False),
        (float(RANGE_DELTA_VALUE), False),
        (Decimal(f"-{RANGE_DELTA_VALUE}.0"), True),
        (Decimal(f"{RANGE_DELTA_VALUE}.0"), True),
        (timezone.now().date(), False),
        (timezone.now(), False),
        (None, False),
    ],
)
@pytest.mark.django_db
def test_base_helper_validate_decimal_value_type(value, is_valid, decimal_span):
    """Test that the `validate_value_type` method of the BaseHelper class works as expected for decimal fields."""
    segment_range = NumericRange(Decimal("0.0"), Decimal(str(RANGE_DELTA_VALUE)))
    segment_instance = ConcreteDecimalSegment.objects.create(span=decimal_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)

    if is_valid:
        base_helper.validate_value_type(value)
    else:
        with pytest.raises(ValueError):
            base_helper.validate_value_type(value)


@pytest.mark.parametrize(
    "value, is_valid",
    [
        (-RANGE_DELTA_VALUE, False),
        (RANGE_DELTA_VALUE, False),
        (float(-RANGE_DELTA_VALUE), False),
        (float(RANGE_DELTA_VALUE), False),
        (Decimal(f"-{RANGE_DELTA_VALUE}.0"), False),
        (Decimal(f"{RANGE_DELTA_VALUE}.0"), False),
        (timezone.now().date(), True),
        (timezone.now(), True),
        (None, False),
    ],
)
@pytest.mark.django_db
def test_base_helper_validate_date_value_type(value, is_valid, date_span):
    """Test that the `validate_value_type` method of the BaseHelper class works as expected for date fields."""
    segment_range = DateRange(date_span.current_range.lower, date_span.current_range.upper)
    segment_instance = ConcreteDateSegment.objects.create(span=date_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)

    if is_valid:
        base_helper.validate_value_type(value)
    else:
        with pytest.raises(ValueError):
            base_helper.validate_value_type(value)


@pytest.mark.parametrize(
    "value, is_valid",
    [
        (-RANGE_DELTA_VALUE, False),
        (RANGE_DELTA_VALUE, False),
        (float(-RANGE_DELTA_VALUE), False),
        (float(RANGE_DELTA_VALUE), False),
        (Decimal(f"-{RANGE_DELTA_VALUE}.0"), False),
        (Decimal(f"{RANGE_DELTA_VALUE}.0"), False),
        (timezone.now().date(), False),
        (timezone.now(), True),
        (None, False),
    ],
)
@pytest.mark.django_db
def test_base_helper_validate_datetime_value_type(value, is_valid, datetime_span):
    """Test that the `validate_value_type` method of the BaseHelper class works as expected for datetime fields."""
    segment_range = DateTimeTZRange(datetime_span.current_range.lower, datetime_span.current_range.upper)
    segment_instance = ConcreteDateTimeSegment.objects.create(span=datetime_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)

    if is_valid:
        base_helper.validate_value_type(value)
    else:
        with pytest.raises(ValueError):
            base_helper.validate_value_type(value)


@pytest.mark.django_db
def test_validate_value_type_invalid_field_type(integer_span):
    """Test that an error is raised when an unsupported field type is used."""
    segment_range = NumericRange(0, RANGE_DELTA_VALUE)
    segment_instance = ConcreteIntegerSegment.objects.create(span=integer_span, segment_range=segment_range)

    base_helper = BaseHelper(segment_instance)
    base_helper.range_field_type = "UnsupportedField"

    with pytest.raises(ValueError):
        base_helper.validate_value_type(RANGE_DELTA_VALUE)
