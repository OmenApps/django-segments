"""Base classes and metaclasses for AbstractSpan and AbstractSegment models."""
from __future__ import annotations

import hashlib
import logging
import typing
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
    RangeOperators,
)
from django.db import models
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
    Range,
)
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from django_segments.app_settings import (
    ALLOW_SEGMENT_GAPS,
    ALLOW_SPAN_GAPS,
    DEFAULT_RELATED_NAME,
    DEFAULT_RELATED_QUERY_NAME,
)
from django_segments.app_settings import DJANGO_SEGMENTS_MODEL_BASE as ModelBase
from django_segments.app_settings import (
    POSTGRES_RANGE_FIELDS,
    PREVIOUS_FIELD_ON_DELETE,
    SOFT_DELETE,
    SPAN_ON_DELETE,
)
from django_segments.exceptions import (
    IncorrectRangeTypeError,
    IncorrectSubclassError,
    InvalidRangeFieldNameError,
)


logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from django_segments.models import AbstractSegment, AbstractSpan


def generate_short_hash(name: str, salt: str = "", length: int = 8) -> str:
    """Generate a hash for the given name string."""
    return hashlib.sha256(f"{salt}{name}".encode()).hexdigest()[:length]


def boundary_helper_factory(range_field_name: str) -> tuple:
    """Factory function to create model methods for setting boundaries on a given range field.

    Args:
        range_field_name (str): The name of the range field.

    Returns:
        tuple: A tuple containing the set_boundaries, set_lower_boundary, and set_upper_boundary methods.
    """

    def _set_boundary(
        instance: Union[AbstractSpan, AbstractSegment],
        range_field_name: str,
        lower: Optional[int] = None,
        upper: Optional[int] = None,
    ):
        """Set the lower, upper, or both boundaries of the range field."""
        model_range_field = getattr(instance, range_field_name, None)

        if model_range_field is None:
            raise InvalidRangeFieldNameError(
                f"Invalid range field name: {range_field_name} does not exist on {instance}"
            )

        if lower is not None:
            validate_value_type(instance=instance, value=lower)
        if upper is not None:
            validate_value_type(instance=instance, value=upper)

        RangeClass = get_range_type(instance)  # pylint: disable=C0103

        if lower is not None:
            print(f"boundary_helper_factory _set_boundary: [{lower=} {model_range_field.upper=})")
            range_value = RangeClass(lower=lower, upper=model_range_field.upper)

            # Set both boundaries
            if upper is not None:
                print(f"boundary_helper_factory _set_boundary: [{lower=} {upper=})")
                range_value = RangeClass(lower=lower, upper=upper)

        elif upper is not None:
            print(f"boundary_helper_factory _set_boundary: [{model_range_field.lower=} {upper=})")
            range_value = RangeClass(lower=model_range_field.lower, upper=upper)

        else:
            raise ValueError("At least one of 'lower' or 'upper' must be provided to set boundaries.")

        # Set the value of the model field to the new range value
        setattr(instance, range_field_name, range_value)
        instance.save()

    def validate_value_type(
        instance: Union[AbstractSpan, AbstractSegment],
        value: Union[int, Decimal, date, datetime],
    ) -> None:
        """Validate the type of the provided value against the range_field_type."""
        if value is None:
            raise ValueError("Value cannot be None")

        SpanConfig = get_span_config(instance)  # pylint: disable=C0103

        if SpanConfig.range_field_type not in POSTGRES_RANGE_FIELDS:
            raise IncorrectRangeTypeError(f"Unsupported field type: {SpanConfig.range_field_type}")

        field_type = POSTGRES_RANGE_FIELDS[SpanConfig.range_field_type].get("value_type")

        if not isinstance(value, field_type):
            raise ValueError(f"Value must be of type {field_type}, not {type(value)}")

    # def validate_delta_value_type(
    #     instance: Union[AbstractSpan, AbstractSegment],
    #     delta_value: Union[int, Decimal, timezone.timedelta],
    # ) -> None:
    #     """Validate the type of the provided delta value against the range_field_type."""
    #     if delta_value is None:
    #         raise ValueError("Delta value cannot be None")

    #     SpanConfig = get_span_config(instance)  # pylint: disable=C0103

    #     if SpanConfig.range_field_type not in POSTGRES_RANGE_FIELDS:
    #         raise IncorrectRangeTypeError(f"Unsupported field type: {SpanConfig.range_field_type}")

    #     delta_type = POSTGRES_RANGE_FIELDS[SpanConfig.range_field_type].get("delta_type")

    #     if not isinstance(delta_value, delta_type):
    #         raise ValueError(f"Delta value must be of type {delta_type}, not {type(delta_value)}")

    def get_range_type(instance: Union[AbstractSpan, AbstractSegment]):
        """Get the range class for the instance based on the range_field_type."""
        try:
            span_config = get_span_config(instance)  # pylint: disable=C0103
            RangeClass = POSTGRES_RANGE_FIELDS[span_config.range_field_type]["range_type"]  # pylint: disable=C0103

        except AttributeError as e:
            raise IncorrectRangeTypeError(f"Range type cannot be obtained for {instance.__class__.__name__}") from e

        return RangeClass

    def get_span_config(instance: Union[AbstractSpan, AbstractSegment]):
        """Return the SpanConfig class for the instance."""
        if not hasattr(instance, "SpanConfig"):
            instance.SpanConfig = SegmentConfigurationHelper.get_span_model(instance).SpanConfig
        return instance.SpanConfig

    def set_boundaries(
        instance: Union[AbstractSpan, AbstractSegment],
        lower: Union[int, Decimal, date, datetime],
        upper: Union[int, Decimal, date, datetime],
    ):
        """Set the lower and upper boundaries of the specified range field."""
        _set_boundary(instance, range_field_name, lower=lower, upper=upper)

    def set_lower_boundary(instance: Union[AbstractSpan, AbstractSegment], value: Union[int, Decimal, date, datetime]):
        """Set the lower boundary of the specified range field."""
        _set_boundary(instance, range_field_name, lower=value)

    def set_upper_boundary(instance: Union[AbstractSpan, AbstractSegment], value: Union[int, Decimal, date, datetime]):
        """Set the upper boundary of the specified range field."""
        _set_boundary(instance, range_field_name, upper=value)

    return (
        set_boundaries,
        set_lower_boundary,
        set_upper_boundary,
    )


class ConcreteModelValidationHelper:  # pylint: disable=R0903
    """Helper class for validating that models are concrete."""

    @staticmethod
    def check_model_is_concrete(model: Union[AbstractSpan, AbstractSegment]) -> None:
        """Check that the model is not abstract."""
        if model._meta.abstract:  # pylint: disable=W0212
            raise IncorrectSubclassError("Concrete subclasses must not be abstract")


class SpanConfigurationHelper:
    """Helper class for retrieving Span model configurations."""

    @staticmethod
    def get_config_attr(model, attr_name: str, default):
        """Given an attribute name and default value, returns the attribute value from the SpanConfig class."""
        if not hasattr(model, "SpanConfig"):
            raise IncorrectSubclassError(f"SpanConfig not defined for {model.__class__.__name__}")

        return getattr(model.SpanConfig, attr_name, default)

    @staticmethod
    def get_range_field_type(model: AbstractSpan) -> Range:
        """Return the range field type for the span model after performing some validation."""
        range_field_type = SpanConfigurationHelper.get_config_attr(model, "range_field_type", None)

        if not range_field_type or range_field_type not in POSTGRES_RANGE_FIELDS:
            raise IncorrectRangeTypeError(f"Unsupported range type for {model.__class__.__name__}")

        return range_field_type

    @staticmethod
    def get_config_dict(model: AbstractSpan) -> dict:
        """Return the configuration options for the span as a dictionary."""
        return {
            "allow_span_gaps": SpanConfigurationHelper.get_config_attr(model, "allow_span_gaps", ALLOW_SPAN_GAPS),
            "allow_segment_gaps": SpanConfigurationHelper.get_config_attr(
                model, "allow_segment_gaps", ALLOW_SEGMENT_GAPS
            ),
            "soft_delete": SpanConfigurationHelper.get_config_attr(model, "soft_delete", SOFT_DELETE),
            "range_field_type": SpanConfigurationHelper.get_range_field_type(model),
        }

    @staticmethod
    def get_segment_class(model_instance: AbstractSpan) -> AbstractSegment:
        """Get the segment class associated with the span model.

        The Segment model has a `span` ForeignKey field that points to the span model. This method returns the Segment
        model that is associated with the span model.
        """
        for related_object in model_instance._meta.related_objects:  # pylint: disable=W0212
            if (
                isinstance(related_object.field, models.ForeignKey)
                and related_object.field.related_model == model_instance.__class__
            ):
                return related_object.related_model
        return None


class SegmentConfigurationHelper:
    """Helper class for retrieving Segment model configurations."""

    @staticmethod
    def get_config_attr(model, attr_name: str, default):
        """Given an attribute name and default value, returns the attribute value from the SegmentConfig class."""
        try:
            return getattr(model.SegmentConfig, attr_name, default)
        except AttributeError as e:
            raise IncorrectSubclassError(f"SegmentConfig attribute not defined for {model.__class__.__name__}") from e

    @staticmethod
    def get_span_model(model: AbstractSegment) -> AbstractSpan:
        """Return the span model for the segment model."""
        span_model = SegmentConfigurationHelper.get_config_attr(model, "span_model", None)

        if not span_model or "AbstractSpan" not in [base.__name__ for base in span_model.__bases__]:
            raise IncorrectSubclassError(f"Span model must be a subclass of AbstractSpan for {model}")

        return span_model

    @staticmethod
    def get_config_dict(model: AbstractSegment) -> dict:
        """Return a dictionary of configuration options."""
        return {
            "span_model": SegmentConfigurationHelper.get_span_model(model),
            # This version assumes we set soft_delete on only the Span model, and it applies to both Span and Segment:
            # "soft_delete": getattr(
            #     SegmentConfigurationHelper.get_span_model(model).SpanConfig, "soft_delete", SOFT_DELETE
            # ),
            # This version assumes we set soft_delete separately on the Span and Segment models:
            "soft_delete": SegmentConfigurationHelper.get_config_attr(model, "soft_delete", SOFT_DELETE),
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


class BaseSpanMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSpan."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new span model is created.

        Validates subclass of AbstractSpan & sets initial_range and current_range for the model.
        """
        logger.debug(
            "Inside BaseSpanMetaclass: cls.__name__=%s, name=%s, bases=%s, attrs=%s, kwargs=%s",
            cls.__name__,
            name,
            bases,
            attrs,
            kwargs,
        )

        model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

        # Validate subclass of AbstractSpan & set initial_range and current_range for the model.
        if not cls.is_valid_subclass(bases):
            raise IncorrectSubclassError("BaseSpanMetaclass applied to incorrect Span MRO")

        cls.setup_span_model(model, name)
        model._meta._expire_cache()
        return model

    @staticmethod
    def is_valid_subclass(bases):
        """Check if the metaclass is applied to the correct subclass."""
        base_list = [base.__name__ for base in bases]
        return any([(len(base_list) == 1 and base_list[0] == "Model"), "AbstractSpan" in base_list])

    @classmethod
    def setup_span_model(cls, model, name):
        """Set up the span model."""
        if "AbstractSpan" in [base.__name__ for base in model.__bases__]:
            ConcreteModelValidationHelper.check_model_is_concrete(model)
            SpanConfigurationHelper.get_range_field_type(model)
            config_dict = SpanConfigurationHelper.get_config_dict(model)

            model.add_to_class(
                "initial_range", config_dict["range_field_type"](_("Initial Range"), blank=True, null=True)
            )
            model.add_to_class(
                "current_range", config_dict["range_field_type"](_("Current Range"), blank=True, null=True)
            )
            model_short_hash = generate_short_hash(name)
            cls.add_indexes(model, model_short_hash)
            cls.add_soft_delete_field(model, model_short_hash, config_dict)

    @staticmethod
    def add_indexes(model, model_short_hash):
        """Add indexes for the initial_range and current_range fields."""
        indexes_list = list(model._meta.indexes)  # pylint: disable=W0212
        indexes_list.extend(
            [
                models.Index(fields=["initial_range"], name=f"initial_range_idx_{model_short_hash}"),
                models.Index(fields=["current_range"], name=f"current_range_idx_{model_short_hash}"),
            ]
        )
        model._meta.indexes = indexes_list  # pylint: disable=W0212

    @staticmethod
    def add_soft_delete_field(model, model_short_hash, config_dict):
        """Add a deleted_at field to the model if soft_delete is enabled."""
        if config_dict["soft_delete"]:
            model.add_to_class(
                "deleted_at",
                models.DateTimeField(
                    _("Deleted At"), null=True, blank=True, help_text=_("The date and time the span was deleted.")
                ),
            )
            indexes_list = list(model._meta.indexes)  # pylint: disable=W0212
            indexes_list.extend(
                [
                    models.Index(
                        fields=["initial_range", "deleted_at"], name=f"init_rng_del_at_idx_{model_short_hash}"
                    ),
                    models.Index(
                        fields=["current_range", "deleted_at"], name=f"curr_rng_del_at_idx_{model_short_hash}"
                    ),
                    models.Index(fields=["deleted_at"], name=f"span_deleted_at_idx_{model_short_hash}"),
                ]
            )
            model._meta.indexes = indexes_list  # pylint: disable=W0212


class BaseSegmentMetaclass(ModelBase):  # pylint: disable=R0903
    """Metaclass for AbstractSegment."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Performs actions that need to take place when a new segment model is created.

        Validates subclass of AbstractSegment & sets segment_range and span for the concrete model.
        """
        logger.debug(
            "Inside BaseSegmentMetaclass: cls.__name__=%s, name=%s, bases=%s, attrs=%s, kwargs=%s",
            cls.__name__,
            name,
            bases,
            attrs,
            kwargs,
        )

        model = super().__new__(cls, name, bases, attrs, **kwargs)  # pylint: disable=E1121

        # Validate subclass of AbstractSegment & set segment_range and span for the concrete model.
        if not cls.is_valid_subclass(bases):
            raise IncorrectSubclassError("BaseSegmentMetaclass applied to incorrect Segment MRO")

        cls.setup_segment_model(model, name)
        model._meta._expire_cache()
        return model

    @staticmethod
    def is_valid_subclass(bases):
        """Check if the model is a valid subclass of AbstractSegment."""
        base_list = [base.__name__ for base in bases]
        return any([(len(base_list) == 1 and base_list[0] == "Model"), "AbstractSegment" in base_list])

    @classmethod
    def setup_segment_model(cls, model, name):
        """Set up the segment model."""
        if "AbstractSegment" in [base.__name__ for base in model.__bases__]:
            ConcreteModelValidationHelper.check_model_is_concrete(model)
            SegmentConfigurationHelper.get_span_model(model)
            config_dict = SegmentConfigurationHelper.get_config_dict(model)

            model.add_to_class(
                "segment_range",
                model.SegmentConfig.span_model.SpanConfig.range_field_type(_("Segment Range"), blank=True, null=True),
            )
            model.add_to_class(
                "span",
                models.ForeignKey(
                    model.SegmentConfig.span_model,
                    null=True,
                    blank=True,
                    on_delete=config_dict["span_on_delete"],
                    related_name="segments",
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

            model_short_hash = generate_short_hash(name)
            cls.add_indexes(model, model_short_hash)
            cls.add_constraints(model, model_short_hash)
            cls.add_soft_delete_field(model, model_short_hash, config_dict)

    @classmethod
    def add_indexes(cls, model, model_short_hash):
        """Add the segment_range index to the model."""
        indexes_list = list(model._meta.indexes)  # pylint: disable=W0212
        indexes_list.append(models.Index(fields=["segment_range"], name=f"segment_range_idx_{model_short_hash}"))
        model._meta.indexes = indexes_list  # pylint: disable=W0212

    @classmethod
    def add_constraints(cls, model, model_short_hash):
        """Ensure that the segment_range does not overlap with other segments associated with the same span."""
        constraints_list = list(model._meta.constraints)  # pylint: disable=W0212
        constraints_list.append(
            ExclusionConstraint(
                name=f"segment_range_excl_{model_short_hash}",
                expressions=[((F("segment_range"), RangeOperators.OVERLAPS), (F("span"), RangeOperators.EQUAL))],
                condition=Q(is_deleted__isnull=True),
            )
        )
        model._meta.constraints = constraints_list  # pylint: disable=W0212

    @classmethod
    def add_soft_delete_field(cls, model, model_short_hash, config_dict):
        """Add the deleted_at field to the model if soft_delete is enabled."""
        if config_dict["soft_delete"]:
            model.add_to_class(
                "deleted_at",
                models.DateTimeField(
                    _("Deleted At"), null=True, blank=True, help_text=_("The date and time the segment was deleted.")
                ),
            )
            indexes_list = list(model._meta.indexes)  # pylint: disable=W0212
            indexes_list.extend(
                [
                    models.Index(fields=["deleted_at"], name=f"seg_del_at_idx_{model_short_hash}"),
                    models.Index(fields=["segment_range", "deleted_at"], name=f"seg_rng_del_at_idx_{model_short_hash}"),
                    models.Index(fields=["span", "deleted_at"], name=f"span_del_at_idx_{model_short_hash}"),
                    models.Index(
                        fields=["previous_segment", "deleted_at"], name=f"prev_seg_del_at_idx_{model_short_hash}"
                    ),
                ]
            )
            model._meta.indexes = indexes_list  # pylint: disable=W0212
