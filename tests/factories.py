"""Factories for creating instances of models for testing purposes."""

from datetime import timedelta
from decimal import Decimal

import factory
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)
from django.utils import timezone

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
)


# A constant value to be used in creating ranges for spans and segments
RANGE_DELTA_VALUE = 4


class ConcreteIntegerSpanFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteIntegerSpan model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteIntegerSpan

    initial_range = NumericRange(0, RANGE_DELTA_VALUE)
    current_range = initial_range


class ConcreteIntegerSegmentFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteIntegerSegment model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteIntegerSegment

    span = factory.SubFactory(ConcreteIntegerSpanFactory)
    segment_range = factory.LazyAttribute(
        lambda obj: NumericRange(
            obj.span.current_range.lower if obj.span.segment_count < 1 else obj.span.last_segment.segment_range.upper,
            obj.span.current_range.lower + RANGE_DELTA_VALUE
            if obj.span.segment_count < 1
            else obj.span.last_segment.segment_range.upper + RANGE_DELTA_VALUE,
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        instance = super()._create(model_class, *args, **kwargs)
        return instance


class ConcreteBigIntegerSpanFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteBigIntegerSpan model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteBigIntegerSpan

    initial_range = NumericRange(0, RANGE_DELTA_VALUE)
    current_range = initial_range


class ConcreteBigIntegerSegmentFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteBigIntegerSegment model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteBigIntegerSegment

    span = factory.SubFactory(ConcreteBigIntegerSpanFactory)
    segment_range = factory.LazyAttribute(
        lambda obj: NumericRange(
            obj.span.current_range.lower if obj.span.segment_count < 1 else obj.span.last_segment.segment_range.upper,
            obj.span.current_range.lower + RANGE_DELTA_VALUE
            if obj.span.segment_count < 1
            else obj.span.last_segment.segment_range.upper + RANGE_DELTA_VALUE,
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        instance = super()._create(model_class, *args, **kwargs)
        return instance


class ConcreteDecimalSpanFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDecimalSpan model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDecimalSpan

    initial_range = NumericRange(Decimal("0.0"), Decimal(f"{RANGE_DELTA_VALUE}.0"))
    current_range = initial_range


class ConcreteDecimalSegmentFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDecimalSegment model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDecimalSegment

    span = factory.SubFactory(ConcreteDecimalSpanFactory)
    segment_range = factory.LazyAttribute(
        lambda obj: NumericRange(
            obj.span.current_range.lower if obj.span.segment_count < 1 else obj.span.last_segment.segment_range.upper,
            obj.span.current_range.lower + Decimal(f"{RANGE_DELTA_VALUE}.0")
            if obj.span.segment_count < 1
            else obj.span.last_segment.segment_range.upper + Decimal(f"{RANGE_DELTA_VALUE}.0"),
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        instance = super()._create(model_class, *args, **kwargs)
        return instance


class ConcreteDateSpanFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDateSpan model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDateSpan

    initial_range = DateRange(timezone.now().date(), (timezone.now() + timedelta(days=RANGE_DELTA_VALUE)).date())
    current_range = initial_range


class ConcreteDateSegmentFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDateSegment model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDateSegment

    span = factory.SubFactory(ConcreteDateSpanFactory)
    segment_range = factory.LazyAttribute(
        lambda obj: DateRange(
            obj.span.current_range.lower if obj.span.segment_count < 1 else obj.span.last_segment.segment_range.upper,
            obj.span.current_range.lower + timedelta(days=RANGE_DELTA_VALUE)
            if obj.span.segment_count < 1
            else obj.span.last_segment.segment_range.upper + timedelta(days=RANGE_DELTA_VALUE),
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        instance = super()._create(model_class, *args, **kwargs)
        return instance


class ConcreteDateTimeSpanFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDateTimeSpan model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDateTimeSpan

    initial_range = DateTimeTZRange(timezone.now(), timezone.now() + timedelta(days=RANGE_DELTA_VALUE))
    current_range = initial_range


class ConcreteDateTimeSegmentFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0903
    """Factory for ConcreteDateTimeSegment model."""

    class Meta:  # pylint: disable=R0903 disable=C0115
        model = ConcreteDateTimeSegment

    span = factory.SubFactory(ConcreteDateTimeSpanFactory)
    segment_range = factory.LazyAttribute(
        lambda obj: DateTimeTZRange(
            obj.span.current_range.lower if obj.span.segment_count < 1 else obj.span.last_segment.segment_range.upper,
            obj.span.current_range.lower + timedelta(days=RANGE_DELTA_VALUE)
            if obj.span.segment_count < 1
            else obj.span.last_segment.segment_range.upper + timedelta(days=RANGE_DELTA_VALUE),
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        instance = super()._create(model_class, *args, **kwargs)
        return instance
