"""This module contains the AbstractSpan class, which is the base class for all Span models."""
import logging
from decimal import Decimal
from typing import Union

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from psycopg2.extras import Range  # psycopg2's base range class

from django_segments.app_settings import ALLOW_SEGMENT_GAPS
from django_segments.app_settings import ALLOW_SPAN_GAPS
from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.app_settings import PREVIOUS_FIELD_ON_DELETE
from django_segments.app_settings import SOFT_DELETE
from django_segments.exceptions import IncorrectRangeTypeError
from django_segments.helpers.span import CreateSpanHelper
from django_segments.helpers.span import DeleteSpanHelper
from django_segments.helpers.span import ShiftLowerSpanHelper
from django_segments.helpers.span import ShiftLowerToValueSpanHelper
from django_segments.helpers.span import ShiftSpanHelper
from django_segments.helpers.span import ShiftUpperSpanHelper
from django_segments.helpers.span import ShiftUpperToValueSpanHelper
from django_segments.models.base import AbstractSpanMetaclass
from django_segments.models.base import boundary_helper_factory


logger = logging.getLogger(__name__)


class AbstractSpan(models.Model, metaclass=AbstractSpanMetaclass):
    """Abstract class from which all Span models should inherit.

    All concrete subclasses of AbstractSpan must define a SpanConfig class, with at minimum a `range_type` (as a range
    field class). If not defined, an IncorrectRangeTypeError will be raised.

    Example:

    .. code-block:: python

        class MySpan(AbstractSpan):
            range_type = DateTimeRangeField

            allow_span_gaps = False  # Overriding a global setting
    """

    _set_initial_lower_boundary, _set_initial_upper_boundary = boundary_helper_factory("initial_range")
    _set_lower_boundary, _set_upper_boundary = boundary_helper_factory("current_range")

    class Meta:  # pylint: disable=C0115 disable=R0903
        abstract = True

    class SpanConfig:  # pylint: disable=R0903
        """Configuration options for the span."""

        # range_type = None

    def get_config_attr(self, attr_name: str, default):
        """Given an attribute name and default value, returns the attribute value from the SpanConfig class."""
        return getattr(self.SpanConfig, attr_name, None) if hasattr(self.SpanConfig, attr_name) else default

    def get_config_dict(self) -> dict[str, bool]:
        """Return the configuration options for the span as a dictionary."""

        range_type = self.get_config_attr("range_type", None)  # Previously verified in the metaclass

        return {
            "range_type": range_type,
            "allow_span_gaps": self.get_config_attr("allow_span_gaps", ALLOW_SPAN_GAPS),
            "allow_segment_gaps": self.get_config_attr("allow_segment_gaps", ALLOW_SEGMENT_GAPS),
            "soft_delete": self.get_config_attr("soft_delete", SOFT_DELETE),
        }

    def get_segment_class(self):
        """Get the segment class from the instance, useful when creating new segments dynamically.

        This method accesses the reverse relation from the segment model to the span model.
        """
        # return self.span.field.related_model
        return self.span.field  # ToDo: Check if this is correct

    def set_initial_lower_boundary(self, value) -> None:
        """Set the lower boundary of the initial range field."""
        self._set_initial_lower_boundary(self, value)

    def set_initial_upper_boundary(self, value) -> None:
        """Set the upper boundary of the initial range field."""
        self._set_initial_upper_boundary(self, value)

    def set_lower_boundary(self, value) -> None:
        """Set the lower boundary of the current range field."""
        self._set_lower_boundary(self, value)

    def set_upper_boundary(self, value) -> None:
        """Set the upper boundary of the current range field."""
        self._set_upper_boundary(self, value)

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
        ShiftLowerToValueSpanHelper(self).shift_lower_to_value(new_value)

    def shift_upper_to_value(self, new_value: Union[int, Decimal, timezone.datetime, timezone.datetime.date]) -> None:
        """Shift the upper boundary of the Span's current_range to the given value."""
        ShiftUpperToValueSpanHelper(self).shift_upper_to_value(new_value)

    def delete(self) -> None:
        """Delete the Span and its associated Segments."""
        DeleteSpanHelper(self).delete()

    def get_segments(self) -> models.QuerySet:
        """Return all segments associated with the span."""
        return self.span.all()

    @property
    def first_segment(self):
        """Return the first segment associated with the span."""
        return self.span.exclude(deleted_at__isnull=False).earliest("segment_range")

    @property
    def last_segment(self):
        """Return the last segment associated with the span."""
        return self.span.exclude(deleted_at__isnull=False).latest("segment_range")
