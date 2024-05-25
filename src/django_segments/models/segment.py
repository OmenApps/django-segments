import logging

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import gettext as _

from django_segments.app_settings import ON_DELETE_FOR_PREVIOUS
from django_segments.app_settings import SEGMENT_MODEL_BASE as ModelBase
from django_segments.base import BoundaryHelper
from django_segments.base import ConcreteModelValidationHelper
from django_segments.base import RangeTypesMatchHelper
from django_segments.exceptions import IncorrectSegmentRangeError
from django_segments.exceptions import IncorrectSubclassError
from django_segments.exceptions import SegmentRangeValidationHelper
from django_segments.exceptions import SegmentSpanValidationHelper


logger = logging.getLogger(__name__)


class AbstractSegment(ModelBase):
    """Abstract class from which all segment models should inherit.

    All concrete subclasses of AbstractSegment must define either `segment_range_field_name` (a string representing the
    name of the range field) or `segment_range` (a range field instance). If both or neither are defined, an
    IncorrectSegmentError will be raised.

    All concrete subclasses of AbstractSegment must define either `segment_span_field_name` (a string representing the
    name of the foreign key field) or `segment_span` (a foreign key field instance). If both or neither are defined, an
    IncorrectSegmentError will be raised.

    When the concrete subclass is created, the segment_range_field and segment_span_field attributes are set to the
    range field and foreign key field instances, respectively. These attributes can be used to access the range field
    and foreign key field instances in the concrete subclass.

    Examples:
        class MySegment(AbstractSegment):
            segment_span = models.ForeignKey(MySpan, on_delete=models.CASCADE)

            segment_range_field_name = 'my_range_field'
            my_range_field = DateTimeRangeField()

        class MyOtherSegment(AbstractSegment):
            segment_range = DateTimeRangeField()

            my_span = models.ForeignKey(MySpan, on_delete=models.CASCADE)
            segment_span_field_name = 'my_span'
    """

    deleted_at = models.DateTimeField(
        _("Deleted at"),
        null=True,
        blank=True,
        help_text=_("The date and time the segment was deleted."),
    )

    previous_segment = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        related_name="next_segment",
        on_delete=ON_DELETE_FOR_PREVIOUS,
    )

    class Meta:  # pylint: disable=C0115 disable=R0903
        abstract = True
        indexes = [
            models.Index(fields=["segment_range"]),
            models.Index(fields=["deleted_at"]),
        ]

    def __new__(cls, name, bases, attrs, **kwargs):
        """Validates subclass of AbstractSegment and sets segment_range_field for the concrete model."""
        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

            for base in bases:
                if base.__name__ == "AbstractSegment":
                    # Ensure that the model is not abstract
                    concrete_validation_helper = ConcreteModelValidationHelper(model)
                    concrete_validation_helper.check_model_is_concrete()

                    # Ensure that the segment_range field is valid
                    segment_validation_helper = SegmentRangeValidationHelper(model)
                    segment_range_field = segment_validation_helper.get_validated_segment_range_field()
                    model.segment_range_field = segment_range_field

                    # Ensure that the segment_span field is valid
                    segment_span_validation_helper = SegmentSpanValidationHelper(model)
                    segment_span_field = segment_span_validation_helper.get_validated_segment_span_field()
                    model.segment_span_field = segment_span_field

                    # Ensure that the segment_range field and span's initial_range field have the same type
                    segment_span_initial_range_field = getattr(segment_span_field, "initial_range", None)
                    range_types_match_helper = RangeTypesMatchHelper(
                        segment_range_field,
                        segment_span_initial_range_field,
                    )
                    range_types_match_helper.validate_range_types_match()

            return model
        except IncorrectSubclassError as e:
            logger.error("Incorrect subclass usage in %s: %s", name, str(e))
            raise e
        except IncorrectSegmentRangeError as e:
            logger.error("Incorrect segment usage in %s: %s", name, str(e))
            raise e
        except ImproperlyConfigured as e:
            logger.error("Improperly configured in %s: %s", name, str(e))
            raise e
        except Exception as e:
            logger.error("Error in %s: %s", name, str(e))
            raise e

    def set_lower_boundary(self, value):
        """Set the lower boundary of the range field."""
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="segment_range_field_name", range_field_attr="segment_range"
        )
        boundary_helper.set_lower_boundary(value)

    def set_upper_boundary(self, value):
        """Set the upper boundary of the range field."""
        boundary_helper = BoundaryHelper(
            model=self, range_field_name_attr="segment_range_field_name", range_field_attr="segment_range"
        )
        boundary_helper.set_upper_boundary(value)

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
        return self.segment_span.first_segment

    @property
    def is_first(self):
        """Return True if the segment is the first segment in the span."""
        return self.segment_span.first_segment == self

    @property
    def last(self):
        """Return the last segment in the span."""
        return self.segment_span.last_segment

    @property
    def is_last(self):
        """Return True if the segment is the last segment in the span."""
        return self.segment_span.last_segment == self

    @property
    def is_first_and_last(self):
        """Return True if the segment is the first and last segment in the span."""
        return self.is_first and self.is_last

    @property
    def is_internal(self):
        """Return True if the segment is not the first or last segment in the span."""
        return not self.is_first_and_last

    @property
    def span(self):
        """Return the span associated with the segment."""
        return getattr(self, self.segment_span_field.name)
