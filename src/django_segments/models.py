"""Models for django_segments."""

import logging

from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import gettext as _

from django_segments.app_settings import ALLOW_GAPS
from django_segments.app_settings import ON_DELETE_FOR_PREVIOUS
from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.app_settings import SEGMENT_MODEL_BASE as ModelBase
from django_segments.app_settings import SOFT_DELETE
from django_segments.app_settings import STICKY_BOUNDARIES
from django_segments.exceptions import IncorrectSegmentRangeError
from django_segments.exceptions import IncorrectSpanRangeError
from django_segments.exceptions import IncorrectSubclassError


logger = logging.getLogger(__name__)


class ConcreteModelValidationHelper:  # pylint: disable=R0903
    """Helper class for validating that models are concrete."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model and error class."""
        self.model = model

    def check_model_is_concrete(self) -> None:
        """Ensure that the model is not abstract."""
        if self.model._meta.abstract:  # pylint: disable=W0212
            raise IncorrectSubclassError("Concrete subclasses must not be abstract")


class RangeTypesMatchHelper:  # pylint: disable=R0903
    """Helper class for validating that two range fields have the same type."""

    def __init__(self, range_field1: models.Field, range_field2: models.Field) -> None:
        """Initialize the helper with the range fields."""
        self.range_field1 = range_field1
        self.range_field2 = range_field2

    def validate_range_types_match(self) -> None:
        """Ensure that the range types match."""
        range_type1 = self.range_field1.get_internal_type()
        range_type2 = self.range_field2.get_internal_type()

        if range_type1 != range_type2:
            raise IncorrectSpanRangeError(
                f"Range field '{self.range_field1}' and range field '{self.range_field2}' must be the same type"
            )


class RangeValidationHelper:
    """Base helper class for validating range models."""

    def __init__(
        self,
        model: type[models.Model],
        range_field_name_attr: str,
        range_field_attr: str,
        error_class: type[Exception],
    ) -> None:
        """Initialize the helper with the model and range attributes."""
        self.model = model
        self.range_field_name_attr = range_field_name_attr
        self.range_field_attr = range_field_attr
        self.error_class = error_class

        self.range_field_name = getattr(self.model, self.range_field_name_attr, None)
        self.range_field = getattr(self.model, self.range_field_attr, None)

    def get_validated_range_field(self) -> models.Field:
        """Return the validated range field."""
        return self.validate_range_field()

    def validate_range_field(self) -> models.Field:
        """Ensure one and only one of range_field_name or range_field is defined."""

        # Ensure that one and only one of range_field_name or range_field is defined
        if self.range_field_name is None and self.range_field is None:
            raise self.error_class(
                f"{self.model.__name__}: Concrete subclasses must define either `{self.range_field_name_attr}` or "
                f"`{self.range_field_attr}`"
            )

        if self.range_field_name is not None and self.range_field is not None:
            raise self.error_class(
                f"{self.model.__name__}: Concrete subclasses must define either `{self.range_field_name_attr}` or "
                f"`{self.range_field_attr}`, not both"
            )

        # If a name is provided, make sure that it is a valid field name, and get the field instance
        if self.range_field_name is not None:
            range_field = self.get_range_field_name_instance()
        else:
            range_field = self.range_field

        # Ensure that the range_field is a valid range field
        if range_field.get_internal_type() not in POSTGRES_RANGE_FIELDS.keys():
            raise self.error_class(
                f"{self.model.__name__}: {self.range_field_name_attr} '{range_field}' must be a PostgreSQL range field"
            )

        return range_field

    def get_range_field_name_instance(self) -> models.Field:
        """Return the range field instance."""
        try:
            return self.model._meta.get_field(self.range_field_name)  # pylint: disable=W0212
        except FieldDoesNotExist as e:
            raise self.error_class(
                f"{self.range_field_name_attr} '{self.range_field_name}' does not exist on {self.model.__name__}"
            ) from e


class SpanInitialRangeValidationHelper(RangeValidationHelper):
    """Helper class for validating initial_range in span models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        super().__init__(model, "initial_range_field_name", "initial_range", IncorrectSpanRangeError)

    def get_validated_initial_range_field(self) -> models.Field:
        """Return the validated initial range field."""
        return self.get_validated_range_field()


class SpanCurrentRangeValidationHelper(RangeValidationHelper):
    """Helper class for validating current_range in span models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        super().__init__(model, "current_range_field_name", "current_range", IncorrectSpanRangeError)

    def get_validated_current_range_field(self) -> models.Field:
        """Return the validated current range field."""
        return self.get_validated_range_field()


class BoundaryHelper:
    """Helper class used by AbstractSpan and AbstractSegment to set the boundaries of the range field."""

    def __init__(
        self,
        model: type[models.Model],
        range_field_name_attr: str,
        range_field_attr: str,
    ) -> None:
        """Initialize the helper with the model and range attributes."""
        self.model = model
        self.range_field_name_attr = range_field_name_attr
        self.range_field_attr = range_field_attr

        self.range_field_name = getattr(self.model, self.range_field_name_attr, None)
        self.range_field = getattr(self.model, self.range_field_attr, None)

    def set_lower_boundary(self, value):
        """Set the lower boundary of the range field."""
        return self._set_boundary(lower=value)

    def set_upper_boundary(self, value):
        """Set the upper boundary of the range field."""
        return self._set_boundary(upper=value)

    def _set_boundary(self, lower=None, upper=None):
        """Set the boundary of the range field."""

        # Ensure that the provided value is of the correct type
        self.validate_value_type(lower)
        self.validate_value_type(upper)

        # Set the boundary
        if lower is not None:
            self.range_field.lower = lower

        if upper is not None:
            self.range_field.upper = upper

        return self.range_field

    def validate_value_type(self, value):
        """Validate the type of the provided value against the field_type."""
        if not self.model.field_type in POSTGRES_RANGE_FIELDS.keys():
            raise ValueError(f"Unsupported field type: {self.model.field_type} not in {POSTGRES_RANGE_FIELDS.keys()=}")

        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key in self.model.field_type and not isinstance(value, val):
                raise ValueError(f"Value must be a {val}, not {type(value)}")
            raise ValueError(f"Unsupported field type: {self.model.field_type}")


class AbstractSpan(ModelBase):
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

    def __new__(cls, name, bases, attrs, **kwargs):
        """Validates subclass of AbstractSpan & sets initial_range_field and current_range_field for the model."""
        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

            for base in bases:
                if base.__name__ == "AbstractSpan":
                    # Ensure that the model is not abstract
                    concrete_validation_helper = ConcreteModelValidationHelper(model)
                    concrete_validation_helper.check_model_is_concrete()

                    # Ensure that the initial_range field is valid
                    span_initial_range_validation_helper = SpanInitialRangeValidationHelper(model)
                    initial_range_field = span_initial_range_validation_helper.get_validated_initial_range_field()
                    model.initial_range_field = initial_range_field

                    # Ensure that the current_range field is valid
                    span_current_range_validation_helper = SpanCurrentRangeValidationHelper(model)
                    current_range_field = span_current_range_validation_helper.get_validated_current_range_field()
                    model.current_range_field = current_range_field

                    # Ensure that the initial_range field and current_range field have the same type
                    range_types_match_helper = RangeTypesMatchHelper(initial_range_field, current_range_field)
                    range_types_match_helper.validate_range_types_match()

            return model
        except IncorrectSubclassError as e:
            logger.error("Incorrect subclass usage in %s: %s", name, str(e))
            raise e
        except IncorrectSpanRangeError as e:
            logger.error("Incorrect span usage in %s: %s", name, str(e))
            raise e
        except Exception as e:
            logger.error("Error in %s: %s", name, str(e))
            raise e

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


class SegmentRangeValidationHelper(RangeValidationHelper):
    """Helper class for validating segment models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        super().__init__(model, "segment_range_field_name", "segment_range", IncorrectSegmentRangeError)

    def get_validated_segment_range_field(self) -> models.Field:
        """Return the validated segment range field."""
        return self.get_validated_range_field()


class SegmentSpanValidationHelper:
    """Helper class for validating that models have valid foreign key to a model that inherits from AbstractSpan.

    This can be a field instance named `segment_span` or a field name specified in `segment_span_field_name` attribute.
    """

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        self.model = model
        self.segment_span_field_name = getattr(self.model, "segment_span_field_name", None)
        self.segment_span = getattr(self.model, "segment_span", None)

    def get_validated_segment_span_field(self) -> models.Field:
        """Return the validated segment span field."""
        return self.validate_segment_span_field()

    def validate_segment_span_field(self) -> models.Field:
        """Ensure one and only one of segment_span_field or segment_span is defined."""
        if self.segment_span_field_name is None and self.segment_span is None:
            raise ImproperlyConfigured(
                "Concrete subclasses must define either `segment_span_field_name` or `segment_span`"
            )

        if self.segment_span_field_name is not None and self.segment_span is not None:
            raise ImproperlyConfigured(
                "Concrete subclasses must define either `segment_span_field_name` or `segment_span`, not both"
            )

        if self.segment_span_field_name is not None:
            return self.get_segment_span_field_instance()
        return self.segment_span

    def get_segment_span_field_instance(self) -> models.Field:
        """Return the segment span field instance."""
        try:
            return self.model._meta.get_field(self.segment_span_field_name)  # pylint: disable=W0212
        except FieldDoesNotExist as e:
            raise ImproperlyConfigured(
                f"segment_span_field_name '{self.segment_span_field_name}' does not exist on {self.model.__name__}"
            ) from e


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
