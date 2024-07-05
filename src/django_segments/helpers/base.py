"""Base class for all segment and span helpers."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING, Type, Union

from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
    RangeOperators,
)
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


def get_allowed_postgres_range_field_type_names() -> list[str]:
    """Get the names of all allowed PostgreSQL range field types."""
    return [type.__name__ for type in POSTGRES_RANGE_FIELDS.keys()]


def get_allowed_postgres_range_field_types() -> list[str]:
    """Get the allowed PostgreSQL range field types."""
    return list(POSTGRES_RANGE_FIELDS.keys())


class BoundaryType(Enum):  # pylint: disable=C0115
    LOWER = auto()
    UPPER = auto()


class BaseHelper:  # pylint: disable=R0903
    """Base class for all segment and span helpers.

    Provides common methods and attributes for all segment and span helpers. It should not be instantiated directly.
    """

    def __init__(self, obj: Union[AbstractSpan, AbstractSegment]):
        self.obj = obj
        self.range_field_type = obj.range_field_type
        self.validate_range_field_type()

        self.value_type = self._get_value_type(self.range_field_type)
        self.delta_value_type = self._get_delta_value_type(self.range_field_type)
        self.range_type = self._get_range_type(self.range_field_type)

        self.range_field_type_name = ""
        self.field_value_type_name = ""
        self._initialize_type_names()

    def _initialize_type_names(self) -> None:
        """Initialize the range field type and value type."""
        for field_name in ["current_range", "segment_range"]:
            if hasattr(self.obj, field_name):
                range_value = getattr(self.obj, field_name)
                range_field = self._get_range_field(field_name)
                if range_field:
                    self.range_field_type_name = range_field.get_internal_type()
                    self.field_value_type_name = type(range_value).__name__
                    return
        raise ValueError("Object must have either a `segment_range` or `current_range` field.")

    def _get_range_field(
        self, field_name: str
    ) -> Union[IntegerRangeField, BigIntegerRangeField, DecimalRangeField, DateRangeField, DateTimeRangeField]:
        """Get the range field from the model."""
        try:
            return self.obj._meta.get_field(field_name)  # pylint: disable=W0212
        except FieldDoesNotExist as e:
            logger.error("FieldDoesNotExist error: %s", e)
            return None

    def validate_range_field_type(self) -> None:
        """Validate that the range field type is allowed."""
        if self.range_field_type not in POSTGRES_RANGE_FIELDS:
            raise ValueError(
                f"Unsupported field type for `segment_range` field: "
                f"{self.range_field_type=} not in {POSTGRES_RANGE_FIELDS=}"
            )

    def validate_value_type(self, value: Union[int, Decimal, date, datetime]) -> None:
        """Validate the type of the provided value against the model's range_field_type."""
        if value is None:
            raise ValueError("Value cannot be None")

        expected_value_type = self._get_value_type(self.range_field_type)
        if not isinstance(value, expected_value_type):
            raise ValueError(
                f"BaseHelper.validate_value_type(): Value must be of type {expected_value_type.__name__}, "
                f"not {type(value).__name__}. Provided value: {value}."
            )

    def validate_delta_value_type(self, delta_value: Union[int, Decimal, timezone.timedelta]) -> None:
        """Validate the type of the provided delta value against the model's range_field_type."""
        if delta_value is None:
            raise ValueError("Delta value cannot be None")

        expected_delta_value_type = self._get_delta_value_type(self.range_field_type)
        if not isinstance(delta_value, expected_delta_value_type):
            raise ValueError(
                "BaseHelper.validate_delta_value_type(): Delta value must be of type "
                f"{expected_delta_value_type.__name__}, "
                f"not {type(delta_value).__name__}. Provided delta value: {delta_value}."
            )

    @staticmethod
    def _get_value_type(
        range_field_type: get_allowed_postgres_range_field_types(),
    ) -> Union[type[int], type[Decimal], type[date], type[datetime]]:
        """Get the expected type for a given range field type."""
        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key is range_field_type:
                return val.get("value_type")
        raise ValueError(f"No value type found for range field type: {range_field_type}")

    @staticmethod
    def _get_delta_value_type(
        range_field_type: get_allowed_postgres_range_field_types(),
    ) -> Union[type[int], type[Decimal], type[timezone.timedelta]]:
        """Get the expected type for a given range field type."""
        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key is range_field_type:
                return val.get("delta_type")
        raise ValueError(f"No delta type found for range field type: {range_field_type}")

    @staticmethod
    def _get_range_type(range_field_type: get_allowed_postgres_range_field_types()) -> Type[Range]:
        """Get the range type from the range field type."""
        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key is range_field_type:
                print(f"_get_range_type {val=} {val.get('range_type')=}")
                return val.get("range_type")
        raise ValueError(f"No range type found for range field type: {range_field_type}")

    def set_boundary(
        self, *, range_field: Range, new_boundary: Union[int, Decimal, datetime, date], boundary_type: BoundaryType
    ) -> Range:
        """Set the boundary of the model range field."""
        return range_field.__class__(
            lower=new_boundary if boundary_type == BoundaryType.LOWER else range_field.lower,
            upper=new_boundary if boundary_type == BoundaryType.UPPER else range_field.upper,
        )
