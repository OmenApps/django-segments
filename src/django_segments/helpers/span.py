import logging

from django.db import models
from django.db import transaction
from django.db.models.expressions import F
from django.utils import timezone

from django_segments.helpers.base import BaseHelper


logger = logging.getLogger(__name__)


class SpanHelperBase(BaseHelper):  # pylint: disable=R0903
    """Base class for span helpers."""

    def __init__(self, obj):
        super().__init__(obj)
        self.config_dict = self.obj.get_config_dict()


class CreateSpanHelper(SpanHelperBase):
    """Helper class for creating spans."""

    @transaction.atomic
    def create(self, *args, **kwargs):
        """Create a new Span instance with initial_range and current_range fields set.

        Optionally create an initial Segment that spans the entire range if needed.
        """
        # Check and initialize range values in kwargs
        initial_range = kwargs.get("initial_range", self.get_default_range_value())
        current_range = kwargs.get("current_range", initial_range)
        kwargs.update(
            {
                "initial_range": initial_range,
                "current_range": current_range,
            }
        )

        # Create the Span instance
        span_instance = self.obj.__class__.objects.create(*args, **kwargs)

        # Optionally create an initial Segment
        if self.config_dict.get("create_initial_segment", False):
            self.create_initial_segment(span_instance)

        return span_instance

    def create_initial_segment(self, obj):
        """Create an initial Segment that spans the entire range of the Span."""
        segment_class = self.obj.get_segment_class()
        segment_range = self.obj.current_range

        segment = segment_class.objects.create(segment_span=obj, segment_range_field=segment_range)
        return segment
