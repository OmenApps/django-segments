import logging

from django.conf import settings
from django.contrib.postgres.fields import BigIntegerRangeField
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.fields import DecimalRangeField
from django.contrib.postgres.fields import IntegerRangeField
from django.db import models
from django.db.models.base import ModelBase
from django.utils.timezone import datetime


logger = logging.getLogger(__name__)


# There is likely no reason ever to change the model base, but it is provided as an setting here for completeness.
SEGMENT_MODEL_BASE = getattr(settings, "SEGMENT_MODEL_BASE", ModelBase)

# Define the allowed PostgreSQL range field types
POSTGRES_RANGE_FIELDS = getattr(
    settings,
    "POSTGRES_RANGE_FIELDS",
    {
        IntegerRangeField.__name__: int,
        BigIntegerRangeField.__name__: int,
        DecimalRangeField.__name__: float,
        DateRangeField.__name__: datetime.date,
        DateTimeRangeField.__name__: datetime,
    },
)

# Define the approach for deletion in the segment's `previous` field.
# This setting should be one of the following:
# - models.CASCADE
# - models.PROTECT
# - models.SET_NULL
# - models.SET_DEFAULT
# - models.SET
# - models.DO_NOTHING
ON_DELETE_FOR_PREVIOUS = getattr(settings, "ON_DELETE_FOR_PREVIOUS", models.CASCADE)

# Global configuration settings for Span models
ALLOW_GAPS = getattr(settings, "ALLOW_GAPS", True)
STICKY_BOUNDARIES = getattr(settings, "STICKY_BOUNDARIES", True)
SOFT_DELETE = getattr(settings, "SOFT_DELETE", True)
