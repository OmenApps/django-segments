"""Models for django_segments."""

import logging

from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.app_settings import SEGMENT_MODEL_BASE as ModelBase
from django_segments.exceptions import IncorrectSegmentRangeError
from django_segments.exceptions import IncorrectSpanRangeError
from django_segments.exceptions import IncorrectSubclassError


logger = logging.getLogger(__name__)


class ConcreteModelValidationHelper:
    """Helper class for validating concrete models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model and error class."""
        self.model = model
        self.error_class = IncorrectSubclassError

    def check_model_is_concrete(self) -> None:
        """Ensure that the model is not abstract."""
        if self.model._meta.abstract:  # pylint: disable=protected-access
            raise self.error_class("Concrete subclasses must not be abstract")


class RangeValidationHelper:
    """Base helper class for validating range models."""

    def __init__(
        self, model: type[models.Model], range_field_name_attr: str, range_field_attr: str, error_class: type[Exception]
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
                f"Concrete subclasses must define either `{self.range_field_name_attr}` or `{self.range_field_attr}`"
            )

        if self.range_field_name is not None and self.range_field is not None:
            raise self.error_class(
                f"Concrete subclasses must define either `{self.range_field_name_attr}` or `{self.range_field_attr}`, "
                "not both"
            )

        # If a name is provided, make sure that it is a valid field name, and get the field instance
        if self.range_field_name is not None:
            range_field = self.get_range_field_name_instance()
        else:
            range_field = self.range_field

        # Ensure that the range_field is a valid range field
        if range_field.get_internal_type() not in POSTGRES_RANGE_FIELDS:
            raise self.error_class(f"{self.range_field_name_attr} '{range_field}' must be a PostgreSQL range field")

        return range_field

    def get_range_field_name_instance(self) -> models.Field:
        """Return the range field instance."""
        try:
            return self.model._meta.get_field(self.range_field_name)  # pylint: disable=protected-access
        except FieldDoesNotExist as e:
            raise self.error_class(
                f"{self.range_field_name_attr} '{self.range_field_name}' does not exist on {self.model.__name__}"
            ) from e


class SpanRangeValidationHelper(RangeValidationHelper):
    """Helper class for validating span models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        super().__init__(model, "initial_range_field_name", "initial_range", IncorrectSpanRangeError)
        self.current_range_field_name_attr = "current_range_field_name"
        self.current_range_field_attr = "current_range"

    def get_validated_initial_range_field(self) -> models.Field:
        """Return the validated initial range field."""
        return self.get_validated_range_field()

    def get_validated_current_range_field(self) -> models.Field:
        """Return the validated current range field."""
        return self.validate_current_range_field()

    def validate_current_range_field(self) -> models.Field:
        """Ensure one and only one of current_range_field or current_range is defined."""
        self.range_field_name_attr = self.current_range_field_name_attr
        self.range_field_attr = self.current_range_field_attr
        return self.validate_range_field()


class AbstractSpan(models.Model):
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

    class Meta:
        abstract = True

    def __new__(cls, name, bases, attrs, **kwargs):
        """Validates subclass of AbstractSpan & sets initial_range_field and current_range_field for the model."""
        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=too-many-function-args

            for base in bases:
                if base.__name__ == "AbstractSpan":
                    concrete_validation_helper = ConcreteModelValidationHelper(model)
                    concrete_validation_helper.check_model_is_concrete()

                    span_validation_helper = SpanRangeValidationHelper(model)
                    initial_range_field = span_validation_helper.get_validated_initial_range_field()
                    model.initial_range_field = initial_range_field

                    current_range_field = span_validation_helper.get_validated_current_range_field()
                    model.current_range_field = current_range_field

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
        else:
            return self.segment_span

    def get_segment_span_field_instance(self) -> models.Field:
        """Return the segment span field instance."""
        try:
            return self.model._meta.get_field(self.segment_span_field_name)  # pylint: disable=protected-access
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

    class Meta:
        abstract = True

    def __new__(cls, name, bases, attrs, **kwargs):
        """Validates subclass of AbstractSegment and sets segment_range_field for the concrete model."""
        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=too-many-function-args

            for base in bases:
                if base.__name__ == "AbstractSegment":
                    concrete_validation_helper = ConcreteModelValidationHelper(model)
                    concrete_validation_helper.check_model_is_concrete()

                    segment_validation_helper = SegmentRangeValidationHelper(model)
                    segment_range_field = segment_validation_helper.get_validated_segment_range_field()
                    model.segment_range_field = segment_range_field

                    segment_span_validation_helper = SegmentSpanValidationHelper(model)
                    segment_span_field = segment_span_validation_helper.get_validated_segment_span_field()
                    model.segment_span_field = segment_span_field

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
