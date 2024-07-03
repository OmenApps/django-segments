"""This module contains the AbstractSpan class, which is the base class for all Span models."""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

from django.db import models
from django.utils import timezone

from django_segments.helpers.span import (
    AppendSegmentToSpanHelper,
    DeleteSpanHelper,
    RelationshipHelper,
    ShiftLowerSpanHelper,
    ShiftSpanHelper,
    ShiftUpperSpanHelper,
)
from django_segments.models.base import (
    BaseSpanMetaclass,
    SpanConfigurationHelper,
    boundary_helper_factory,
)


logger = logging.getLogger(__name__)


class SpanQuerySet(models.QuerySet):
    """Custom QuerySet for Span models.

    Models inheriting from AbstractSpan will have access to this custom QuerySet. For custom methods, use this
    QuerySet as a base class and add your custom methods.
    """

    def active(self):
        """Return only active spans."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Return only deleted spans."""
        return self.filter(deleted_at__isnull=False)


class SpanManager(models.Manager):  # pylint: disable=R0903
    """Custom Manager for Span models.

    Models inheriting from AbstractSpan will have access to this custom Manager. For custom methods, use this Manager
    as a base class and add your custom methods.
    """

    def get_queryset(self):
        """Return the custom QuerySet for Span models."""
        return super().get_queryset().prefetch_related("segments")


class AbstractSpan(models.Model, metaclass=BaseSpanMetaclass):
    """Abstract class from which all Span models should inherit.

    All concrete subclasses of AbstractSpan must define a SpanConfig class, with at minimum a `range_field_type`.
    If not defined, an IncorrectRangeTypeError will be raised.

    Example:

    .. code-block:: python

        class MySpan(AbstractSpan):
            class SpanConfig:
                range_field_type = DateTimeRangeField

                allow_span_gaps = False  # Overriding a global setting
    """

    _set_initial_lower_boundary, _set_initial_upper_boundary = boundary_helper_factory("initial_range")
    _set_lower_boundary, _set_upper_boundary = boundary_helper_factory("current_range")

    objects = SpanManager.from_queryset(SpanQuerySet)()

    class Meta:  # pylint: disable=C0115 disable=R0903
        abstract = True
        indexes = []

        # print(f"{_BaseSpan.Meta=}")
        # print(f"{dir(_BaseSpan.Meta)=}")
        # print(f"{_BaseSpan.Meta.__dict__=}")
        # print(f"{_BaseSpan.Meta.__dict__.items()=}")
        # print(f"{_BaseSpan.Meta.__dict__.get('indexes')=}")
        # print(f"{_BaseSpan.Meta.__dict__.get('constraints')=}")

    class SpanConfig:  # pylint: disable=R0903
        """Configuration options for the span."""

    def get_config_dict(self) -> dict[str, bool]:
        """Return the configuration options for the span as a dictionary."""

        return SpanConfigurationHelper.get_config_dict(self)

    def get_segment_class(self):
        """Get the segment class. This is a helper method to get the segment class associated with this Span."""
        return SpanConfigurationHelper.get_segment_class(self)

    def set_initial_lower_boundary(self, value) -> None:
        """Set the lower boundary of the initial range field."""
        self._set_initial_lower_boundary(value)

    def set_initial_upper_boundary(self, value) -> None:
        """Set the upper boundary of the initial range field."""
        self._set_initial_upper_boundary(value)

    def set_lower_boundary(self, value) -> None:
        """Set the lower boundary of the current range field."""
        self._set_lower_boundary(value)

    def set_upper_boundary(self, value) -> None:
        """Set the upper boundary of the current range field."""
        self._set_upper_boundary(value)

    def shift_by_value(self, value: Union[int, Decimal, timezone.timedelta]) -> None:
        """Shift the range value of the entire Span and each of its associated Segments by the given value."""
        ShiftSpanHelper(self).shift_by_value(value)

    def shift_lower_by_value(self, value: Union[int, Decimal, timezone.timedelta]) -> None:
        """Shift the lower boundary of the Span's current_range by the given value."""
        ShiftLowerSpanHelper(self).shift_lower_by_value(value)

    def shift_upper_by_value(self, value: Union[int, Decimal, timezone.timedelta]) -> None:
        """Shift the upper boundary of the Span's current_range by the given value."""
        ShiftUpperSpanHelper(self).shift_upper_by_value(value)

    def shift_lower_to_value(self, new_value: Union[int, Decimal, timezone.datetime, timezone.datetime.date]) -> None:
        """Shift the lower boundary of the Span's current_range to the given value."""
        ShiftLowerSpanHelper(self).shift_lower_to_value(new_value)

    def shift_upper_to_value(self, new_value: Union[int, Decimal, timezone.datetime, timezone.datetime.date]) -> None:
        """Shift the upper boundary of the Span's current_range to the given value."""
        ShiftUpperSpanHelper(self).shift_upper_to_value(new_value)

    def append(
        self,
        to_value: Optional[Union[int, Decimal, date, datetime]] = None,
        delta_value: Optional[Union[int, Decimal, timezone.timedelta]] = None,
        **kwargs,
    ) -> None:
        """Append a new Segment to the Span using the given value or delta value."""
        return AppendSegmentToSpanHelper(self).append(to_value=to_value, delta_value=delta_value, **kwargs)

    def delete(self) -> None:
        """Delete the Span and its associated Segments."""
        DeleteSpanHelper(self).delete()

    def get_segments(self) -> models.QuerySet:
        """Return all segments associated with the span."""
        return self.segments.all().order_by("segment_range")

    def get_active_segments(self) -> models.QuerySet:
        """Return all active segments associated with the span."""
        return self.segments.exclude(deleted_at__isnull=False).order_by("segment_range")

    def get_inactive_segments(self) -> models.QuerySet:
        """Return all inactive segments associated with the span."""
        return self.segments.filter(deleted_at__isnull=False).order_by("segment_range")

    @property
    def segment_count(self) -> int:
        """Return the number of segments associated with the span."""
        return self.get_active_segments().count()

    @property
    def first_segment(self):
        """Return the first segment associated with the span."""
        return self.segments.exclude(deleted_at__isnull=False).earliest("segment_range")

    @property
    def last_segment(self):
        """Return the last segment associated with the span."""
        return self.segments.exclude(deleted_at__isnull=False).latest("segment_range")

    def check_and_fix_relationships(self):
        """Check and fix the relationships between the span and its segments."""
        RelationshipHelper(self).check_and_fix_relationships()
