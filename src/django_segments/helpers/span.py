import logging

from django.db import models
from django.db import transaction
from django.db.models.expressions import F
from django.utils import timezone
from psycopg2.extras import Range  # psycopg2's base range class

from django_segments.helpers.base import BaseHelper
from django_segments.signals import segment_created
from django_segments.signals import span_created


logger = logging.getLogger(__name__)


class SpanHelperBase(BaseHelper):  # pylint: disable=R0903
    """Base class for span helpers."""

    def __init__(self, obj):
        super().__init__(obj)
        self.config_dict = self.obj.get_config_dict()


class CreateSpanHelper(SpanHelperBase):
    """Helper class for creating spans."""

    @transaction.atomic
    def create(self, *args, range_value: Range = None, **kwargs):
        """Create a new Span instance with initial_range and current_range fields set.

        Optionally create an initial Segment that spans the entire range if needed.
        """
        # Initialize range values in kwargs
        kwargs.update({"initial_range": range_value, "current_range": range_value})

        # Create the Span instance
        span_instance = self.obj.__class__.objects.create(*args, **kwargs)
        span_created.send(sender=self.obj.__class__, instance=span_instance)  # Send signal

        self.create_initial_segment(span_instance)

        return span_instance

    def create_initial_segment(self, obj):
        """Create an initial Segment that spans the entire range of the Span."""
        segment_class = self.obj.get_segment_class()
        segment_range = self.obj.current_range

        segment = segment_class.objects.create(segment_span=obj, segment_range_field=segment_range)
        segment_created.send(sender=segment_class, instance=segment)  # Send signal
        return segment
