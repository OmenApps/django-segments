"""This module contains the AbstractSegment class, which is the base class for all Segment models."""
import logging

from django.db import models
from django.utils import timezone

from django_segments.helpers.segment import (
    AppendSegmentHelper,
    CreateSegmentHelper,
    DeleteSegmentHelper,
    InsertSegmentHelper,
    MergeSegmentHelper,
    ShiftLowerSegmentHelper,
    ShiftSegmentHelper,
    ShiftUpperSegmentHelper,
    SplitSegmentHelper,
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

    _set_lower_boundary, _set_upper_boundary = boundary_helper_factory("segment_range")

    objects = SegmentManager.from_queryset(SegmentQuerySet)()

    class Meta:  # pylint: disable=C0115 disable=R0903 disable=W0212
        abstract = True
        indexes = []

    class SegmentConfig:  # pylint: disable=R0903
        """Configuration options for the segment."""

    def get_config_dict(self) -> dict[str, bool]:
        """Return a dictionary of configuration options."""

        return SegmentConfigurationHelper.get_config_dict(self)

    @property
    def span_config(self):
        """Return the configuration options for the segment's parent span."""
        return self.span.get_config_dict()

    @staticmethod
    def create(*args, span, segment_range, **kwargs):
        """Create a new Segment instance."""
        return CreateSegmentHelper(*args, span=span, segment_range=segment_range, **kwargs).create()

    def set_lower_boundary(self, value) -> None:
        """Set the lower boundary of the segment range field."""
        self._set_lower_boundary(value)

    def set_upper_boundary(self, value) -> None:
        """Set the upper boundary of the segment range field."""
        self._set_upper_boundary(value)

    def shift_by_value(self, value):
        """Shift the range value of the entire Segment."""
        ShiftSegmentHelper(self).shift_by_value(value)

    def shift_lower_by_value(self, value):
        """Shift the lower boundary of the Segment's segment_range by the given value."""
        ShiftLowerSegmentHelper(self).shift_lower_by_value(value)

    def shift_upper_by_value(self, value):
        """Shift the upper boundary of the Segment's segment_range by the given value."""
        ShiftUpperSegmentHelper(self).shift_upper_by_value(value)

    def shift_lower_to_value(self, new_value):
        """Shift the lower boundary of the Segment's segment_range to the given value."""
        ShiftLowerSegmentHelper(self).shift_lower_to_value(new_value)

    def shift_upper_to_value(self, new_value):
        """Shift the upper boundary of the Segment's segment_range to the given value."""
        ShiftUpperSegmentHelper(self).shift_upper_to_value(new_value)

    def split(self, split_value, fields_to_copy=None):
        """Split the segment into two at the provided value."""
        SplitSegmentHelper(self).split(split_value, fields_to_copy)

    def merge_into_upper(self):
        """Merge the segment into the next (upper) segment."""
        MergeSegmentHelper(self).merge_into_upper()

    def merge_into_lower(self):
        """Merge the segment into the previous (lower) segment."""
        MergeSegmentHelper(self).merge_into_lower()

    def append(self, value):
        """Append a segment with the specified range."""
        AppendSegmentHelper(self).append(value)

    def insert(self, span, segment_range):
        """Insert a new segment into the span."""
        InsertSegmentHelper(self).insert(span, segment_range)

    def delete(self):
        """Delete the Segment."""
        if self.get_config_dict().get("soft_delete"):
            print("soft deleting segment")
            DeleteSegmentHelper(self).soft_delete()
        else:
            print("hard deleting segment")
            segment_pre_delete_or_soft_delete.send(sender=self.__class__)  # Send signal
            segment_pre_delete.send(sender=self.__class__)  # Send signal
            super().delete()
            segment_post_delete.send(sender=self.__class__)  # Send signal
            segment_post_delete_or_soft_delete.send(sender=self.__class__)  # Send signal

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
