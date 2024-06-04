"""This module contains the AbstractSegment class, which is the base class for all Segment models."""
import logging

from django.db import models
from django.utils.translation import gettext as _

from django_segments.app_settings import DEFAULT_RELATED_NAME
from django_segments.app_settings import DEFAULT_RELATED_QUERY_NAME
from django_segments.app_settings import PREVIOUS_FIELD_ON_DELETE
from django_segments.app_settings import SOFT_DELETE
from django_segments.app_settings import SPAN_ON_DELETE
from django_segments.models.base import AbstractSegmentMetaclass
from django_segments.models.base import SegmentConfigurationHelper
from django_segments.models.base import boundary_helper_factory


logger = logging.getLogger(__name__)


class AbstractSegment(models.Model, metaclass=AbstractSegmentMetaclass):
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

    class Meta:  # pylint: disable=C0115 disable=R0903
        abstract = True

    class SegmentConfig:  # pylint: disable=R0903
        """Configuration options for the segment."""

    def get_config_dict(self) -> dict[str, bool]:
        """Return a dictionary of configuration options."""

        return SegmentConfigurationHelper.get_config_dict(self)

    def set_lower_boundary(self, value) -> None:
        """Set the lower boundary of the segment range field."""
        self._set_lower_boundary(self, value)

    def set_upper_boundary(self, value) -> None:
        """Set the upper boundary of the segment range field."""
        self._set_upper_boundary(self, value)

    @property
    def previous(self):
        """Return the previous segment."""
        return self.previous_segment

    @property
    def next(self):
        """Return the next segment."""
        return self.next_segment

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
    def is_internal(self):
        """Return True if the segment is not the first or last segment in the span."""
        return not self.is_first_and_last
