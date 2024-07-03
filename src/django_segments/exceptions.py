"""Exceptions for the django_segments package."""

from django.core.exceptions import FieldError, ImproperlyConfigured


class IncorrectSubclassError(ImproperlyConfigured):
    """Raised when a subclass of BaseSegment is not correctly implemented."""


class IncorrectSegmentRangeError(FieldError):
    """Raised when a segment model's range field is not correctly implemented."""


class IncorrectSpanRangeError(FieldError):
    """Raised when a span model's range fields are not correctly implemented."""


class IncorrectRangeTypeError(FieldError):
    """Raised when the range type is not one of the supported types specified in the settings."""


class InvalidRangeFieldNameError(FieldError):
    """Raised when the field specified by range_field_name does not exist on the model."""


class SegmentRelationshipError(FieldError):
    """Raised when the segment instances for a span are not related correctly by previous_segment."""
