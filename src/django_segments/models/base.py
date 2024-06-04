"""Base classes and metaclasses for AbstractSpan and AbstractSegment models."""

import logging

from django.db import models
from django.utils.translation import gettext as _

from django_segments.app_settings import ALLOW_SEGMENT_GAPS
from django_segments.app_settings import ALLOW_SPAN_GAPS
from django_segments.app_settings import DEFAULT_RELATED_NAME
from django_segments.app_settings import DEFAULT_RELATED_QUERY_NAME
from django_segments.app_settings import DJANGO_SEGMENTS_MODEL_BASE as ModelBase
from django_segments.app_settings import POSTGRES_RANGE_FIELDS
from django_segments.app_settings import PREVIOUS_FIELD_ON_DELETE
from django_segments.app_settings import SOFT_DELETE
from django_segments.app_settings import SPAN_ON_DELETE
from django_segments.exceptions import IncorrectRangeTypeError
from django_segments.exceptions import IncorrectSubclassError


logger = logging.getLogger(__name__)


def boundary_helper_factory(range_field_name):
    """Factory function to create set_lower_boundary and set_upper_boundary model methods for a given range field.

    Args:
        range_field_name (str): The name of the range field.

    Returns:
        tuple: A tuple containing the set_lower_boundary and set_upper_boundary methods.
    """

    def _set_boundary(self, range_field_name, lower=None, upper=None):
        """Set the boundary of the range field."""

        range_field = getattr(self.model, range_field_name, None)
        validate_value_type(self, value=lower if lower is not None else upper)

        if lower is not None:
            range_field.lower = lower

        if upper is not None:
            range_field.upper = upper

        setattr(self.model, range_field_name, range_field)

    def validate_value_type(self, value):
        """Validate the type of the provided value against the field_type."""
        if value is None:
            raise ValueError("Value cannot be None")

        if not self.model.field_type in POSTGRES_RANGE_FIELDS.keys():
            raise ValueError(f"Unsupported field type: {self.model.field_type} not in {POSTGRES_RANGE_FIELDS.keys()=}")

        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key in self.model.field_type and not isinstance(value, val):
                raise ValueError(f"Value must be a {val}, not {type(value)}")
            raise ValueError(f"Unsupported field type: {self.model.field_type}")

    def set_lower_boundary(self, value):
        """Set the lower boundary of the specified range field."""
        _set_boundary(self, range_field_name, lower=value)

    def set_upper_boundary(self, value):
        """Set the upper boundary of the specified range field."""
        _set_boundary(self, range_field_name, upper=value)

    return (
        set_lower_boundary,
        set_upper_boundary,
    )


class ConcreteModelValidationHelper:  # pylint: disable=R0903
    """Helper class for validating that models are concrete."""

    @staticmethod
    def check_model_is_concrete(model) -> None:
        """Check that the model is not abstract."""
        if model._meta.abstract:  # pylint: disable=W0212
            raise IncorrectSubclassError("Concrete subclasses must not be abstract")


class SpanConfigurationHelper:
    """Helper class for retrieving Span model configurations."""

    @staticmethod
    def get_config_attr(model, attr_name: str, default):
        """Given an attribute name and default value, returns the attribute value from the SpanConfig class."""
        return getattr(model.SpanConfig, attr_name, default)

    @staticmethod
    def get_range_type(model):
        """Return the range type for the span model."""
        range_type = SpanConfigurationHelper.get_config_attr(model, "range_type", None)
        if range_type is None:
            raise IncorrectRangeTypeError(f"Range type not defined for {model.__class__.__name__}")
        if range_type.__name__ not in POSTGRES_RANGE_FIELDS:
            raise IncorrectRangeTypeError(
                f"Unsupported range type: {range_type} not in {POSTGRES_RANGE_FIELDS.keys()} for "
                f"{model.__class__.__name__}"
            )
        return range_type

    @staticmethod
    def get_config_dict(model) -> dict:
        """Return the configuration options for the span as a dictionary."""
        return {
            "allow_span_gaps": SpanConfigurationHelper.get_config_attr(model, "allow_span_gaps", ALLOW_SPAN_GAPS),
            "allow_segment_gaps": SpanConfigurationHelper.get_config_attr(
                model, "allow_segment_gaps", ALLOW_SEGMENT_GAPS
            ),
            "soft_delete": SpanConfigurationHelper.get_config_attr(model, "soft_delete", SOFT_DELETE),
            "range_type": SpanConfigurationHelper.get_range_type(model),
        }


class SegmentConfigurationHelper:
    """Helper class for retrieving Segment model configurations."""

    @staticmethod
    def get_config_attr(model, attr_name: str, default):
        """Given an attribute name and default value, returns the attribute value from the SegmentConfig class."""
        return getattr(model.SegmentConfig, attr_name, default)

    @staticmethod
    def get_span_model(model):
        """Return the span model for the segment model."""
        span_model = SegmentConfigurationHelper.get_config_attr(model, "span_model", None)
        if span_model is None:
            raise IncorrectSubclassError(_(f"Span model not defined for {model.__class__.__name__}"))
        if "AbstractSpan" not in [base.__name__ for base in span_model.__bases__]:
            raise IncorrectSubclassError(_(f"Span model ({span_model}) must be a subclass of AbstractSpan for {model}"))
        return span_model

    @staticmethod
    def get_config_dict(model) -> dict:
        """Return a dictionary of configuration options."""
        return {
            "span_model": SegmentConfigurationHelper.get_span_model(model),
            "soft_delete": getattr(
                SegmentConfigurationHelper.get_span_model(model).SpanConfig, "soft_delete", SOFT_DELETE
            ),
            "previous_field_on_delete": SegmentConfigurationHelper.get_config_attr(
                model, "previous_field_on_delete", PREVIOUS_FIELD_ON_DELETE
            ),
            "span_on_delete": SegmentConfigurationHelper.get_config_attr(model, "span_on_delete", SPAN_ON_DELETE),
            "span_related_name": SegmentConfigurationHelper.get_config_attr(
                model, "span_related_name", DEFAULT_RELATED_NAME
            ),
            "span_related_query_name": SegmentConfigurationHelper.get_config_attr(
                model, "span_related_query_name", DEFAULT_RELATED_QUERY_NAME
            ),
        }


class AbstractSpanMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSpan."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new span model is created.

        Validates subclass of AbstractSpan & sets initial_range and current_range for the model.
        """
        logger.debug("Creating new span model: %s", name)

        model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

        for base in bases:
            if base.__name__ == "AbstractSpan":
                # Call get_range_type to ensure that the range type is defined
                SpanConfigurationHelper.get_range_type(model)

                # Ensure that the model is not abstract
                ConcreteModelValidationHelper.check_model_is_concrete(model)

                config_dict = SpanConfigurationHelper.get_config_dict(model)

                # Add the initial_range and current_range fields to the model
                model.add_to_class(
                    "initial_range",
                    config_dict["range_type"](
                        _("Initial Range"),
                        blank=True,
                        null=True,
                    ),
                )

                model.add_to_class(
                    "current_range",
                    config_dict["range_type"](
                        _("Current Range"),
                        blank=True,
                        null=True,
                    ),
                )

                # Add indexes to the model's Meta class
                if not hasattr(model.Meta, "indexes"):
                    model.Meta.indexes = [
                        models.Index(fields=["initial_range"]),
                        models.Index(fields=["current_range"]),
                    ]

                # If we are using soft delete, add a deleted_at field to the model
                if config_dict["soft_delete"]:
                    model.add_to_class(
                        "deleted_at",
                        models.DateTimeField(
                            _("Deleted At"),
                            null=True,
                            blank=True,
                            help_text=_("The date and time the span was deleted."),
                        ),
                    )

                    # Add an index for the deleted_at field
                    model.Meta.indexes.append(models.Index(fields=["deleted_at"]))

        return model


class AbstractSegmentMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSegment."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new segment model is created.

        Validates subclass of AbstractSegment & sets segment_range and span for the concrete model.
        """
        logger.debug("Creating new segment model: %s", name)

        model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

        for base in bases:
            if base.__name__ == "AbstractSegment":
                # Call get_span_model to ensure that the span model is defined
                SegmentConfigurationHelper.get_span_model(model)

                # Ensure that the model is not abstract
                ConcreteModelValidationHelper.check_model_is_concrete(model)

                config_dict = SegmentConfigurationHelper.get_config_dict(model)

                # Add the segment_range, span, and previous_segment fields to the model
                model.add_to_class(
                    "segment_range",
                    model.SegmentConfig.span_model.SpanConfig.range_type(
                        _("Segment Range"),
                        blank=True,
                        null=True,
                    ),
                )

                model.add_to_class(
                    "span",
                    models.ForeignKey(
                        model.SegmentConfig.span_model,
                        null=True,
                        blank=True,
                        on_delete=config_dict["span_on_delete"],
                        related_name=config_dict["span_related_name"],
                        related_query_name=config_dict["span_related_query_name"],
                    ),
                )

                model.add_to_class(
                    "previous_segment",
                    models.OneToOneField(
                        model,
                        null=True,
                        blank=True,
                        on_delete=config_dict["previous_field_on_delete"],
                        related_name="next_segment",
                    ),
                )

                # Add indexes to the model's Meta class
                if not hasattr(model.Meta, "indexes"):
                    model.Meta.indexes = [
                        models.Index(fields=["segment_range"]),
                    ]
                else:
                    model.Meta.indexes.append(models.Index(fields=["segment_range"]))

                # If we are using soft delete, add a deleted_at field to the model
                if config_dict["soft_delete"]:
                    model.add_to_class(
                        "deleted_at",
                        models.DateTimeField(
                            _("Deleted At"),
                            null=True,
                            blank=True,
                            help_text=_("The date and time the segment was deleted."),
                        ),
                    )

                    # Add an index for the deleted_at field
                    model.Meta.indexes.append(models.Index(fields=["deleted_at"]))

        return model
