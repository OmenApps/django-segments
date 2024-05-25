"""Models for django_segments."""

import logging

from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.signals import class_prepared
from django.utils.translation import gettext as _

from django_segments.app_settings import DJANGO_SEGMENTS_MODEL_BASE as ModelBase
from django_segments.app_settings import POSTGRES_RANGE_FIELDS
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

        logger.debug("RangeTypesMatchHelper __init__(): %s, %s", type(self.range_field1), type(self.range_field2))

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

        logger.debug(
            "RangeValidationHelper __init__(): %s, %s, %s, %s",
            self.model,
            self.range_field_name_attr,
            self.range_field_attr,
            self.error_class,
        )

        self.range_field_name = getattr(self.model, self.range_field_name_attr, None)
        range_field_deferred_attr = getattr(self.model, self.range_field_attr, None)

        self.range_field = getattr(range_field_deferred_attr, "field", None) if range_field_deferred_attr else None
        logger.debug("RangeValidationHelper __init__(): %s, %s", self.range_field_name, self.range_field)

    def get_validated_range_field(self) -> models.Field:
        """Return the validated range field."""
        return self.validate_range_field()

    def validate_range_field(self) -> models.Field:
        """Ensure one and only one of range_field_name or range_field is defined."""
        logger.debug("RangeValidationHelper validate_range_field(): %s, %s", self.range_field_name, self.range_field)

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


class SegmentRangeValidationHelper(RangeValidationHelper):
    """Helper class for validating segment models."""

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        super().__init__(model, "segment_range_field_name", "segment_range", IncorrectSegmentRangeError)

    def get_validated_segment_range_field(self) -> models.Field:
        """Return the validated segment range field."""
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


class SegmentSpanValidationHelper:
    """Helper class for validating that models have valid foreign key to a model that inherits from AbstractSpan.

    This can be a field instance named `segment_span` or a field name specified in `segment_span_field_name` attribute.
    """

    def __init__(self, model: type[models.Model]) -> None:
        """Initialize the helper with the model."""
        self.model = model
        self.segment_span_field_name = getattr(self.model, "segment_span_field_name", None)

        segment_span_deferred_attr = getattr(self.model, "segment_span", None)
        self.segment_span = getattr(segment_span_deferred_attr, "field", None) if segment_span_deferred_attr else None
        logger.debug(
            "SegmentSpanValidationHelper __init__(): %s, %s, %s",
            self.model,
            self.segment_span_field_name,
            self.segment_span,
        )

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


class AbstractSpanMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSpan."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new span model is created.

        Validates subclass of AbstractSpan & sets initial_range_field and current_range_field for the model.
        """
        logger.debug("Creating new span model: %s", name)

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
                logger.debug(
                    "AbstractSpanMetaclass passing to RangeTypesMatchHelper: %s, %s",
                    type(initial_range_field),
                    type(current_range_field),
                )
                range_types_match_helper = RangeTypesMatchHelper(initial_range_field, current_range_field)
                range_types_match_helper.validate_range_types_match()

        # Log the `dir` of the model
        logger.debug("AbstractSpanMetaclass dir(model): %s", dir(model))

        return model


class AbstractSegmentMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSegment."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new segment model is created.

        Validates subclass of AbstractSegment & sets segment_range_field and segment_span_field for the concrete model.
        """
        logger.debug("Creating new segment model: %s", name)

        model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

        def late_binding(sender, **kwargs):  # pylint: disable=W0613
            """Late binding to ensure that the segment_range_field is set after the model is prepared.

            If we try to access the segment_range_field in the related Span model before the models are prepared,
                we will get an AttributeError.
            """
            if sender is model:
                for base in bases:
                    if base.__name__ == "AbstractSegment":
                        # Ensure that the model is not abstract
                        concrete_validation_helper = ConcreteModelValidationHelper(model)
                        concrete_validation_helper.check_model_is_concrete()

                        # Ensure that the segment_range field is valid
                        segment_validation_helper = SegmentRangeValidationHelper(model)
                        segment_range_field = segment_validation_helper.get_validated_segment_range_field()
                        model.segment_range_field = segment_range_field  # pylint: disable=W0201

                        # Ensure that the segment_span field is valid
                        segment_span_validation_helper = SegmentSpanValidationHelper(model)
                        segment_span_field = segment_span_validation_helper.get_validated_segment_span_field()
                        model.segment_span_field = segment_span_field  # pylint: disable=W0201

                        # Ensure that the segment_range field and span's initial_range field have the same type
                        related_model = segment_span_field.related_model
                        segment_span_initial_range_field = getattr(related_model, "initial_range_field", None)

                        if not segment_span_initial_range_field:
                            raise ImproperlyConfigured(
                                f"{related_model.__name__} must have an 'initial_range_field' attribute"
                            )

                        logger.debug(
                            "AbstractSegmentMetaclass passing to RangeTypesMatchHelper: %s, %s",
                            type(segment_range_field),
                            type(segment_span_initial_range_field),
                        )
                        range_types_match_helper = RangeTypesMatchHelper(
                            segment_range_field,
                            segment_span_initial_range_field,
                        )
                        range_types_match_helper.validate_range_types_match()

        class_prepared.connect(late_binding, sender=model)

        # Log the `dir` of the model
        logger.debug("AbstractSegmentMetaclass dir(model): %s", dir(model))

        return model
