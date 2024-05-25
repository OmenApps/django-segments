import logging

from django.db import models
from django.utils.translation import gettext as _

from django_segments.app_settings import ALLOW_GAPS
from django_segments.app_settings import SOFT_DELETE
from django_segments.app_settings import STICKY_BOUNDARIES
from django_segments.models.base import AbstractSegmentMetaclass
from django_segments.models.base import BoundaryHelper


logger = logging.getLogger(__name__)


class AbstractSpan(models.Model, metaclass=AbstractSegmentMetaclass):
    """Abstract class from which all span models should inherit.

    All concrete subclasses of AbstractSpan must define either `initial_range_field_name` (a string representing the
    name of the range field) or `initial_range` (a range field instance). If both or neither are defined, an
    IncorrectSpan will be raised.

    All concrete subclasses of AbstractSpan must define either `current_range_field_name` (a string representing the
    name of the range field) or `current_range` (a range field instance). If both or neither are defined, an
    IncorrectSpan will be raised.

    When the concrete subclass is created, the initial_range_field and current_range_field attributes set to the range
    field instances. These attributes can be used to access the range field instances in the concrete subclass.

    Examples:
        class MySpan(AbstractSpan):
            my_range_field = DateTimeRangeField()
            initial_range_field_name = 'my_range_field'

            current_range = DateTimeRangeField()
    """

    deleted_at = models.DateTimeField(
        _("Deleted at"),
        null=True,
        blank=True,
        help_text=_("The date and time the span was deleted."),
    )

    class Meta:  # pylint: disable=C0115 disable=R0903
        abstract = True
        indexes = [
            models.Index(fields=["initial_range"]),
            models.Index(fields=["current_range"]),
            models.Index(fields=["deleted_at"]),
        ]

    class Config:  # pylint: disable=R0903
        """Configuration options for the span."""

        allow_gaps = ALLOW_GAPS
        sticky_boundaries = STICKY_BOUNDARIES
        soft_delete = SOFT_DELETE

    def get_config_dict(self) -> dict[str, bool]:
        """Return the configuration options for the span as a dictionary."""
        return {
            "allow_gaps": self.Config.allow_gaps,
            "sticky_boundaries": self.Config.sticky_boundaries,
            "soft_delete": self.Config.soft_delete,
        }

    def get_segment_class(self):
        """Get the segment class from the instance, useful when creating new segments dynamically.

        This method accesses the reverse relation from the segment model to the span model.
        """
        # return self.segment_span.field.related_model
        return self.segment_span.field

    def set_initial_lower_boundary(self, value):
        """Set the lower boundary of the initial range field.

        Only used when creating a new span.
        """
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="initial_range_field_name", range_field_attr="initial_range"
        )
        boundary_helper.set_lower_boundary(value)

    def set_initial_upper_boundary(self, value):
        """Set the upper boundary of the initial range field.

        Only used when creating a new span.
        """
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="initial_range_field_name", range_field_attr="initial_range"
        )
        boundary_helper.set_upper_boundary(value)

    def set_lower_boundary(self, value):
        """Set the lower boundary of the current range field."""
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="current_range_field_name", range_field_attr="current_range"
        )
        boundary_helper.set_lower_boundary(value)

    def set_upper_boundary(self, value):
        """Set the upper boundary of the current range field."""
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="current_range_field_name", range_field_attr="current_range"
        )
        boundary_helper.set_upper_boundary(value)

    def get_segments(self):
        """Return all segments associated with the span."""
        return self.segment_span.all()

    @property
    def first_segment(self):
        """Return the first segment associated with the span."""
        return self.segment_span.exclude(deleted_at__isnull=False).earliest("segment_range")

    @property
    def last_segment(self):
        """Return the last segment associated with the span."""
        return self.segment_span.exclude(deleted_at__isnull=False).latest("segment_range")
