"""This module contains fixtures that are used in multiple tests."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)
from django.utils import timezone

from tests.factories import (
    RANGE_DELTA_VALUE,
    ConcreteBigIntegerSegmentFactory,
    ConcreteBigIntegerSpanFactory,
    ConcreteDateSegmentFactory,
    ConcreteDateSpanFactory,
    ConcreteDateTimeSegmentFactory,
    ConcreteDateTimeSpanFactory,
    ConcreteDecimalSegmentFactory,
    ConcreteDecimalSpanFactory,
    ConcreteIntegerSegmentFactory,
    ConcreteIntegerSpanFactory,
)


@pytest.fixture
def integer_span():
    """Return a ConcreteIntegerSpanFactory instance."""
    span = ConcreteIntegerSpanFactory()
    print(f"integer_span ** {span=}")
    return span


@pytest.fixture
def integer_segment():
    """Return a ConcreteIntegerSegmentFactory instance."""
    span = ConcreteIntegerSpanFactory()
    segment = ConcreteIntegerSegmentFactory(span=span, segment_range=NumericRange(0, RANGE_DELTA_VALUE))
    segment.save()
    print(f"integer_segment ** {span=}, {segment=}, {segment.span=}, {segment.segment_range=}")
    return segment


@pytest.fixture
def integer_span_and_segments():
    """Return a ConcreteIntegerSpanFactory instance and a list of ConcreteIntegerSegmentFactory instances."""
    span = ConcreteIntegerSpanFactory()
    span.current_range = NumericRange(0, (RANGE_DELTA_VALUE) * 3)
    span.save()

    segment1 = ConcreteIntegerSegmentFactory(span=span, segment_range=NumericRange(0, RANGE_DELTA_VALUE))
    segment2 = ConcreteIntegerSegmentFactory(
        span=span,
        previous_segment=segment1,
        segment_range=NumericRange(RANGE_DELTA_VALUE, RANGE_DELTA_VALUE * 2),
    )
    segment3 = ConcreteIntegerSegmentFactory(
        span=span,
        previous_segment=segment2,
        segment_range=NumericRange(RANGE_DELTA_VALUE * 2, RANGE_DELTA_VALUE * 3),
    )
    segment1.save()
    segment2.save()
    segment3.save()
    print(f"integer_span_and_segments ** {span=}, {segment1=}, {segment1.span=}, {segment1.segment_range=}, {segment2=}, {segment2.span=}, {segment2.segment_range=}, {segment3=}, {segment3.span=}, {segment3.segment_range=}")
    print(f"integer_span_and_segments ** {span.segments.all()=}")
    return span, [segment1, segment2, segment3]


@pytest.fixture
def big_integer_span():
    """Return a ConcreteBigIntegerSpanFactory instance."""
    return ConcreteBigIntegerSpanFactory()


@pytest.fixture
def big_integer_segment(big_integer_span):
    """Return a ConcreteBigIntegerSegmentFactory instance."""
    return ConcreteBigIntegerSegmentFactory(span=big_integer_span, segment_range=NumericRange(0, RANGE_DELTA_VALUE))


@pytest.fixture
def big_integer_span_and_segments(big_integer_span):
    """Return a ConcreteBigIntegerSpanFactory instance and a list of ConcreteBigIntegerSegmentFactory instances."""
    big_integer_span.current_range = NumericRange(0, (RANGE_DELTA_VALUE) * 3)
    big_integer_span.save()

    segment1 = ConcreteBigIntegerSegmentFactory(span=big_integer_span, segment_range=NumericRange(0, RANGE_DELTA_VALUE))
    segment2 = ConcreteBigIntegerSegmentFactory(
        span=big_integer_span,
        previous_segment=segment1,
        segment_range=NumericRange(RANGE_DELTA_VALUE, RANGE_DELTA_VALUE * 2),
    )
    segment3 = ConcreteBigIntegerSegmentFactory(
        span=big_integer_span,
        previous_segment=segment2,
        segment_range=NumericRange(RANGE_DELTA_VALUE * 2, RANGE_DELTA_VALUE * 3),
    )
    return big_integer_span, [segment1, segment2, segment3]


@pytest.fixture
def decimal_span():
    """Return a ConcreteDecimalSpanFactory instance."""
    return ConcreteDecimalSpanFactory()


@pytest.fixture
def decimal_segment(decimal_span):
    """Return a ConcreteDecimalSegmentFactory instance."""
    return ConcreteDecimalSegmentFactory(
        span=decimal_span, segment_range=NumericRange(Decimal("0.0"), Decimal(f"{RANGE_DELTA_VALUE}.0"))
    )


@pytest.fixture
def decimal_span_and_segments(decimal_span):
    """Return a ConcreteDecimalSpanFactory instance and a list of ConcreteDecimalSegmentFactory instances."""
    decimal_span.current_range = NumericRange(Decimal("0.0"), Decimal(f"{RANGE_DELTA_VALUE}.0") * 3)
    decimal_span.save()

    segment1 = ConcreteDecimalSegmentFactory(
        span=decimal_span, segment_range=NumericRange(Decimal("0.0"), Decimal(f"{RANGE_DELTA_VALUE}.0"))
    )
    segment2 = ConcreteDecimalSegmentFactory(
        span=decimal_span,
        previous_segment=segment1,
        segment_range=NumericRange(Decimal(f"{RANGE_DELTA_VALUE}.0"), Decimal(f"{RANGE_DELTA_VALUE * 2}.0")),
    )
    segment3 = ConcreteDecimalSegmentFactory(
        span=decimal_span,
        previous_segment=segment2,
        segment_range=NumericRange(Decimal(f"{RANGE_DELTA_VALUE * 2}.0"), Decimal(f"{RANGE_DELTA_VALUE * 3}.0")),
    )
    return decimal_span, [segment1, segment2, segment3]


@pytest.fixture
def date_span():
    """Return a ConcreteDateSpanFactory instance."""
    return ConcreteDateSpanFactory()


@pytest.fixture
def date_segment(date_span):
    """Return a ConcreteDateSegmentFactory instance."""
    return ConcreteDateSegmentFactory(
        span=date_span,
        segment_range=DateRange(
            timezone.now().date(), (timezone.now() + timezone.timedelta(days=RANGE_DELTA_VALUE)).date()
        ),
    )


@pytest.fixture
def date_span_and_segments(date_span):
    """Return a ConcreteDateSpanFactory instance and a list of ConcreteDateSegmentFactory instances."""
    date_span.current_range = DateRange(
        date_span.current_range.lower, date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 3)
    )
    date_span.save()

    segment1 = ConcreteDateSegmentFactory(
        span=date_span,
        segment_range=DateRange(
            date_span.current_range.lower, date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE)
        ),
    )
    segment2 = ConcreteDateSegmentFactory(
        span=date_span,
        previous_segment=segment1,
        segment_range=DateRange(
            date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE),
            date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 2),
        ),
    )
    segment3 = ConcreteDateSegmentFactory(
        span=date_span,
        previous_segment=segment2,
        segment_range=DateRange(
            date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 2),
            date_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 3),
        ),
    )
    return date_span, [segment1, segment2, segment3]


@pytest.fixture
def datetime_span():
    """Return a ConcreteDateTimeSpanFactory instance."""
    return ConcreteDateTimeSpanFactory()


@pytest.fixture
def datetime_segment(datetime_span):
    """Return a ConcreteDateTimeSegmentFactory instance."""
    return ConcreteDateTimeSegmentFactory(
        span=datetime_span,
        segment_range=DateTimeTZRange(timezone.now(), timezone.now() + timezone.timedelta(days=RANGE_DELTA_VALUE)),
    )


@pytest.fixture
def datetime_span_and_segments(datetime_span):
    """Return a ConcreteDateTimeSpanFactory instance and a list of ConcreteDateTimeSegmentFactory instances."""
    datetime_span.current_range = DateTimeTZRange(
        datetime_span.current_range.lower,
        datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 3),
    )
    datetime_span.save()

    segment1 = ConcreteDateTimeSegmentFactory(
        span=datetime_span,
        segment_range=DateTimeTZRange(
            datetime_span.current_range.lower,
            datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE),
        ),
    )
    segment2 = ConcreteDateTimeSegmentFactory(
        span=datetime_span,
        previous_segment=segment1,
        segment_range=DateTimeTZRange(
            datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE),
            datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 2),
        ),
    )
    segment3 = ConcreteDateTimeSegmentFactory(
        span=datetime_span,
        previous_segment=segment2,
        segment_range=DateTimeTZRange(
            datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 2),
            datetime_span.current_range.lower + timezone.timedelta(days=RANGE_DELTA_VALUE * 3),
        ),
    )
    return datetime_span, [segment1, segment2, segment3]
