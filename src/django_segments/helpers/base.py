"""Base class for all segment and span helpers."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Union

from django_segments.app_settings import POSTGRES_RANGE_FIELDS


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from django_segments.models import BaseSegment
    from django_segments.models import BaseSpan


class BaseHelper:  # pylint: disable=R0903
    """Base class for all segment and span helpers."""

    field_type = None
    obj = None

    def __init__(self, obj: Union[BaseSpan, BaseSegment]):
        self.obj = obj

        # Get the field_type, which tells us the type of range field used in the model
        segment_range = getattr(self.obj, 'segment_range', None)
        if segment_range:
            self.field_type = segment_range.get_internal_type()

    def validate_value_type(self, value):
        """Validate the type of the provided value against the model's field_type."""
        if value is None:
            raise ValueError("Value cannot be None")

        if not self.field_type in POSTGRES_RANGE_FIELDS.keys():
            raise ValueError(f"Unsupported field type: {self.field_type} not in {POSTGRES_RANGE_FIELDS.keys()=}")

        for key, val in POSTGRES_RANGE_FIELDS.items():
            if key in self.field_type and not isinstance(value, val):
                raise ValueError(f"Value must be a {val}, not {type(value)}")
            raise ValueError(f"Unsupported field type: {self.field_type}")
