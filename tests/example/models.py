"""Models for the example app."""


from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.db import models
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)

from django_segments.models.segment import (
    AbstractSegment,
    SegmentManager,
    SegmentQuerySet,
)
from django_segments.models.span import AbstractSpan


class EventSpan(AbstractSpan):  # pylint: disable=R0903
    """A span of time that contains event segments."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        """Configuration options for the span."""

        range_field_type = DateTimeRangeField

        allow_span_gaps = False

    def __str__(self):
        return f"Initial: {self.initial_range} - Current: {self.current_range}"

    class Meta:  # pylint: disable=C0115 disable=R0903
        indexes = []


class EventSegment(AbstractSegment):  # pylint: disable=R0903
    """A segment of time within an event span."""

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        """Configuration options for the segment."""

        span_model = EventSpan

        previous_field_on_delete = models.CASCADE
        span_on_delete = models.SET_NULL

    def __str__(self):
        return f"Segment Range: {self.segment_range}"

    class Meta:  # pylint: disable=C0115 disable=R0903
        indexes = []


class InheritedMetaSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with a Meta class inherited from AbstractSpan."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = IntegerRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True

    class Meta(AbstractSpan.Meta):  # pylint: disable=C0115 disable=R0903
        pass


class InheritedMetaSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with a Meta class inherited from AbstractSegment."""

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = InheritedMetaSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True

    class Meta(AbstractSegment.Meta):  # pylint: disable=C0115 disable=R0903
        pass


class ConcreteIntegerSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with IntegerRangeField for testing."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = IntegerRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True


class ConcreteBigIntegerSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with BigIntegerRangeField for testing."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = BigIntegerRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True


class ConcreteDecimalSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with DecimalRangeField for testing."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = DecimalRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True


class ConcreteDateSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with DateRangeField for testing."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = DateRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True


class ConcreteDateTimeSpan(AbstractSpan):  # pylint: disable=R0903
    """Concrete implementation of AbstractSpan with DateTimeRangeField for testing."""

    class SpanConfig:  # pylint: disable=C0115 disable=R0903
        range_field_type = DateTimeRangeField
        allow_span_gaps = True
        allow_segment_gaps = True
        soft_delete = True


class ConcreteIntegerSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with IntegerRangeField for testing."""

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = ConcreteIntegerSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True


class ConcreteBigIntegerSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with BigIntegerRangeField for testing."""

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = ConcreteBigIntegerSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True


class ConcreteDecimalSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with DecimalRangeField for testing."""

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = ConcreteDecimalSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True


class ConcreteDateSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with DateRangeField for testing."""

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = ConcreteDateSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True


class ConcreteDateTimeSegment(AbstractSegment):  # pylint: disable=R0903
    """Concrete implementation of AbstractSegment with DateTimeRangeField for testing."""

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class SegmentConfig:  # pylint: disable=C0115 disable=R0903
        span_model = ConcreteDateTimeSpan
        previous_field_on_delete = models.CASCADE
        span_on_delete = models.CASCADE
        soft_delete = True
