"""Settings for the Django Segments app.

This module provides the global settings for the Django Segments app. These settings can be overridden by setting the
same attributes in the Django settings module.

Attributes:
    DJANGO_SEGMENTS_MODEL_BASE (ModelBase): The base class for all models in the Django Segments app. This setting can
        be overridden to change the base class for all models in the Django Segments app. The default value is
        `ModelBase`.
    POSTGRES_RANGE_FIELDS (dict): A dictionary of allowed PostgreSQL range field types. The key is the field name and
        the value is the Python type that should be used to represent the range field. The default value is a
        dictionary containing the following key-value pairs:
        - `IntegerRangeField.__name__`: `int`
        - `BigIntegerRangeField.__name__`: `int`
        - `DecimalRangeField.__name__`: `Decimal`
        - `DateRangeField.__name__`: `date`
        - `DateTimeRangeField.__name__`: `datetime`
    PREVIOUS_FIELD_ON_DELETE (int): The approach for deletion in the segment's `previous` field. This setting should be
        one of the following:
        - `models.CASCADE`
        - `models.PROTECT`
        - `models.SET_NULL`
        - `models.SET_DEFAULT`
        - `models.SET`
        - `models.DO_NOTHING`
    ALLOW_SPAN_GAPS (bool): Global configuration setting for allowing gaps in spans. This setting can be overridden by
        setting the same attribute on the concrete Span model. The default value is `True`.
    ALLOW_SEGMENT_GAPS (bool): Global configuration setting for allowing gaps in segments. This setting can be
        overridden by setting the same attribute on the concrete Span model. The default value is `True`.
    SOFT_DELETE (bool): Global configuration setting for soft deletion. This setting can be overridden by setting the
        same attribute on the concrete Span model. The default value is `True`. If `True`, the `deleted_at` field will
        be added to the model and used for soft deletion.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.db import models
from django.db.backends.postgresql.psycopg_any import (
    DateRange,
    DateTimeTZRange,
    NumericRange,
)
from django.db.models.base import ModelBase


logger = logging.getLogger(__name__)


# There is likely no reason ever to change the model base, but it is provided as an setting here for completeness.
DJANGO_SEGMENTS_MODEL_BASE = getattr(settings, "DJANGO_SEGMENTS_MODEL_BASE", ModelBase)

# Define the allowed PostgreSQL range field types as a dictionary where the key is the field name and the value is the
# Python type that should be used to represent the range field.
POSTGRES_RANGE_FIELDS = getattr(
    settings,
    "POSTGRES_RANGE_FIELDS",
    {
        IntegerRangeField.__name__: {
            "type": int,
            "range": NumericRange,
        },
        BigIntegerRangeField.__name__: {
            "type": int,
            "range": NumericRange,
        },
        DecimalRangeField.__name__: {
            "type": Decimal,
            "range": NumericRange,
        },
        DateRangeField.__name__: {
            "type": date,
            "range": DateRange,
        },
        DateTimeRangeField.__name__: {
            "type": datetime,
            "range": DateTimeTZRange,
        },
    },
)

DEFAULT_RELATED_NAME = "%(app_label)s_%(class)s_related"
DEFAULT_RELATED_QUERY_NAME = "%(app_label)s_%(class)ss"


# Global configuration settings for Span models.
# These settings can be overridden by setting the same attributes on the concrete Span model.
ALLOW_SPAN_GAPS = getattr(settings, "ALLOW_SPAN_GAPS", True)
ALLOW_SEGMENT_GAPS = getattr(settings, "ALLOW_SEGMENT_GAPS", True)
SOFT_DELETE = getattr(settings, "SOFT_DELETE", True)

# Global configuration settings for Segment models.
# These settings can be overridden by setting the same attributes on the concrete Segment model.
PREVIOUS_FIELD_ON_DELETE = getattr(settings, "PREVIOUS_FIELD_ON_DELETE", models.CASCADE)
SPAN_ON_DELETE = getattr(settings, "SPAN_ON_DELETE", models.CASCADE)
