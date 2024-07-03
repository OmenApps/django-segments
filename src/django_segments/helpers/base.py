"""Base class for all segment and span helpers."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING, Type, Union

from django.core.exceptions import FieldDoesNotExist
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
    Range,
)
from django.utils import timezone

from django_segments.app_settings import POSTGRES_RANGE_FIELDS


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from django_segments.models import AbstractSegment, AbstractSpan


class BoundaryType(Enum):  # pylint: disable=C0115
    LOWER = auto()
    UPPER = auto()


class BaseHelper:  # pylint: disable=R0903
    """Base class for all segment and span helpers."""

    def __init__(self, obj: Union[AbstractSpan, AbstractSegment]):
        self.obj = obj
        self.range_field_type = None
        self.field_value_type = None
        self._initialize_range_field()

    def _initialize_range_field(self) -> None:
        """Initialize the range field type and value type."""
        for field_name in ["current_range", "segment_range"]:
            if hasattr(self.obj, field_name):
                range_value = getattr(self.obj, field_name)
                range_field = self._get_range_field(field_name)
                if range_field:
                    self.range_field_type = range_field.get_internal_type()
                    self.field_value_type = type(range_value).__name__
                    return
        raise ValueError("Object must have either a `segment_range` or `current_range` field.")

    def _get_range_field(self, field_name: str) -> Type:
        """Get the range field from the model."""
        try:
            return self.obj._meta.get_field(field_name)  # pylint: disable=W0212
        except FieldDoesNotExist as e:
            logger.error("FieldDoesNotExist error: %s", e)
            return None

    def validate_value_type(self, value: Union[int, Decimal, date, datetime]) -> None:
        """Validate the type of the provided value against the model's range_field_type."""
        if value is None:
            raise ValueError("Value cannot be None")

        if self.range_field_type not in POSTGRES_RANGE_FIELDS:
            raise ValueError(
                f"Unsupported field type for `segment_range` field: "
                f"{self.range_field_type=} not in {POSTGRES_RANGE_FIELDS.keys()=}"
            )

        expected_type = self._get_expected_type(self.range_field_type)
        if not isinstance(value, expected_type):
            raise ValueError(
                f"BaseHelper.validate_value_type(): Value must be of type {expected_type.__name__}, "
                f"not {type(value).__name__}. Provided value: {value}."
            )

    @staticmethod
    def _get_expected_type(range_field_type: str) -> Type:
        """Get the expected type for a given range field type."""
        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key in range_field_type:
                return val.get("type")
        raise ValueError(f"No expected type found for range field type: {range_field_type}")

    def set_boundary(
        self, range_field: Range, new_boundary: Union[int, Decimal, datetime, date], boundary_type: BoundaryType
    ) -> Range:
        """Set the boundary of the range field."""
        return range_field.__class__(
            lower=new_boundary if boundary_type == BoundaryType.LOWER else range_field.lower,
            upper=new_boundary if boundary_type == BoundaryType.UPPER else range_field.upper,
        )

    def validate_range(
        self,
        range_value: Union[Range, DateRange, DateTimeTZRange, NumericRange],
        lower_bound: Union[int, Decimal, datetime, date],
        upper_bound: Union[int, Decimal, datetime, date],
    ) -> None:
        """Validate that the range is within the specified bounds."""
        if range_value.lower < lower_bound or range_value.upper > upper_bound:
            raise ValueError("Range must be within the specified bounds.")
