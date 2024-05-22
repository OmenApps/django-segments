from django.conf import settings
from django.contrib.postgres.fields import BigIntegerRangeField
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.fields import DecimalRangeField
from django.contrib.postgres.fields import IntegerRangeField
from django.db.models.base import ModelBase


# There is likely no reason ever to change the model base, but it is provided as an setting here for completeness.
SEGMENT_MODEL_BASE = getattr(settings, "SEGMENT_MODEL_BASE", ModelBase)

# Define the allowed PostgreSQL range field types
POSTGRES_RANGE_FIELDS = getattr(
    settings,
    "POSTGRES_RANGE_FIELDS",
    (
        IntegerRangeField,
        BigIntegerRangeField,
        DecimalRangeField,
        DateRangeField,
        DateTimeRangeField,
    ),
)
