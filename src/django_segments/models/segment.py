"""This module contains the AbstractSegment class, which is the base class for all Segment models."""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

from django.db import models
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
    Range,
)
from django.utils import timezone

from django_segments.context_managers import SegmentDeleteSignalContext
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
from django_segments.helpers.span import (
    AppendSegmentToSpanHelper,
    SpanConfigurationHelper,
)
from django_segments.models.base import (
    BaseSegmentMetaclass,
    SegmentConfigurationHelper,
    boundary_helper_factory,
    generate_short_hash,
)
from django_segments.signals import (
    segment_post_delete,
    segment_post_delete_or_soft_delete,
    segment_pre_delete,
    segment_pre_delete_or_soft_delete,
)


logger = logging.getLogger(__name__)


class SegmentQuerySet(models.QuerySet):
    """Custom QuerySet for Segment models.

    Models inheriting from AbstractSegment will have access to this custom QuerySet. For custom methods, use this
    QuerySet as a base class and add your custom methods.
    """

    def active(self):
        """Return only active segments."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Return only deleted segments."""
        return self.filter(deleted_at__isnull=False)


class SegmentManager(models.Manager):
    """Custom Manager for Segment models.

    Models inheriting from AbstractSegment will have access to this custom Manager. For custom methods, use this Manager
    as a base class and add your custom methods.
    """

    def get_queryset(self):
        """Return a custom queryset."""
        return super().get_queryset().select_related("span")

    def create(self, span, segment_range, **kwargs):
        """Uses the Segment's create method to create a new Segment instance."""
        segment = self.model.create(span=span, segment_range=segment_range, **kwargs)

        return segment


class AbstractSegment(models.Model, metaclass=BaseSegmentMetaclass):  # pylint: disable=R0904
    """Abstract class from which all Segment models should inherit.

    All concrete subclasses of AbstractSegment must define a SegmentConfig class, with at minimum a `span_model` (as a
    subclass of AbstractSpan). If not defined, an IncorrectSubclassError will be raised.

    Examples:

    .. code-block:: python

        class MySegment(AbstractSegment):
            span_model = MySpan

            previous_field_on_delete = models.SET_NULL  # Overriding a global setting

        class MyOtherSegment(AbstractSegment):
            span_model = MyOtherSpan
    """

    _set_boundaries, _set_lower_boundary, _set_upper_boundary = boundary_helper_factory("segment_range")

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class Meta:  # pylint: disable=C0115 disable=R0903 disable=W0212
        abstract = True
        indexes = []

    class SegmentConfig:  # pylint: disable=R0903
        """Configuration options for the segment."""

    def _get_config_dict(self) -> dict[str, bool]:
        """Return a dictionary of configuration options."""

        return SegmentConfigurationHelper.get_config_dict(self)

    @property
    def _span_config(self):
        """Return the configuration options for the segment's parent span."""
        return self.span.get_config_dict()

    @property
    def _range_field_type(self):
        """Return the range field type."""
        return SpanConfigurationHelper.get_range_field_type(self.span)

    @staticmethod
    def _create(*, span, segment_range, **kwargs):
        """Create a new Segment instance."""
        return CreateSegmentHelper(span=span, segment_range=segment_range, **kwargs).create()

    def _set_boundaries(
        self, lower_boundary: Union[int, Decimal, datetime, date], upper_boundary: Union[int, Decimal, datetime, date]
    ) -> None:
        """Set both boundaries of the segment range field."""
        self._set_boundaries(lower_boundary, upper_boundary)

    def _set_lower_boundary(self, value) -> None:
        """Set the lower boundary of the segment range field."""
        self._set_lower_boundary(value)

    def _set_upper_boundary(self, value) -> None:
        """Set the upper boundary of the segment range field."""
        self._set_upper_boundary(value)

    def shift_by_value(self, delta_value):
        """Shift the range value of the entire Segment."""
        ShiftSegmentHelper(self).shift_by_value(delta_value=delta_value)

    def shift_lower_by_value(self, delta_value):
        """Shift the lower boundary of the Segment's segment_range by the given value."""
        ShiftLowerSegmentHelper(self).shift_lower_by_value(delta_value=delta_value)

    def shift_upper_by_value(self, delta_value):
        """Shift the upper boundary of the Segment's segment_range by the given value."""
        ShiftUpperSegmentHelper(self).shift_upper_by_value(delta_value=delta_value)

    def shift_lower_to_value(self, to_value: Union[int, Decimal, datetime, date]) -> None:
        """Shift the lower boundary of the Segment's segment_range to the given value."""
        ShiftLowerSegmentHelper(self).shift_lower_to_value(to_value=to_value)

    def shift_upper_to_value(self, to_value: Union[int, Decimal, datetime, date]) -> None:
        """Shift the upper boundary of the Segment's segment_range to the given value."""
        ShiftUpperSegmentHelper(self).shift_upper_to_value(to_value=to_value)

    def split(self, split_value, fields_to_copy=None):
        """Split the segment into two at the provided value."""
        SplitSegmentHelper(self).split(split_value=split_value, fields_to_copy=fields_to_copy)

    def merge_into_upper(self):
        """Merge the segment into the next (upper) segment."""
        MergeSegmentHelper(self).merge_into_upper()

    def merge_into_lower(self):
        """Merge the segment into the previous (lower) segment."""
        MergeSegmentHelper(self).merge_into_lower()

    def append(
        self,
        to_value: Optional[Union[int, Decimal, date, datetime, Range]] = None,
        delta_value: Optional[Union[int, Decimal, timezone.timedelta]] = None,
        **kwargs,
    ) -> None:
        """Append a Segment to using the given value or delta value."""
        return AppendSegmentToSpanHelper(self.span).append(to_value=to_value, delta_value=delta_value, **kwargs)

    def insert(self, *, span: models.Model, segment_range: Union[Range, DateRange, DateTimeTZRange, NumericRange]):
        """Insert a new segment into the span."""
        InsertSegmentHelper(self).insert(span, segment_range)

    def delete(self):
        """Delete the Segment."""
        if self._get_config_dict().get("soft_delete"):
            # print("soft deleting segment")
            DeleteSegmentHelper(self).soft_delete()
        else:
            # print("hard deleting segment")
            with SegmentDeleteSignalContext(self):
                super().delete()

    @property
    def previous(self):
        """Return the previous segment."""
        return self.previous_segment or None

    @property
    def next(self):
        """Return the next segment."""
        # Note: We use getattr since this is a reverse relation, and we cannot access `next_segment` directly
        return getattr(self, "next_segment", None)

    @property
    def first(self):
        """Return the first segment in the span."""
        return self.span.first_segment

    @property
    def is_first(self):
        """Return True if the segment is the first segment in the span."""
        return self.span.first_segment == self

    @property
    def last(self):
        """Return the last segment in the span."""
        return self.span.last_segment

    @property
    def is_last(self):
        """Return True if the segment is the last segment in the span."""
        return self.span.last_segment == self

    @property
    def is_first_and_last(self):
        """Return True if the segment is the first and last segment in the span."""
        return self.is_first and self.is_last

    @property
    def is_first_or_last(self):
        """Return True if the segment is the first and last segment in the span."""
        return self.is_first or self.is_last

    @property
    def is_internal(self):
        """Return True if the segment is not the first or last segment in the span."""
        return not self.is_first_or_last

    @property
    def is_active(self):
        """Return True if the segment is not deleted."""
        return self.deleted_at is None

    @property
    def is_deleted(self):
        """Return True if the segment is deleted."""
        return self.deleted_at is not None
