"""Models for django_segments."""

import logging

from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import gettext as _

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
