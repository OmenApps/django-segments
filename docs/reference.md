# Reference

```{eval-rst}
admin.py
========

.. automodule:: django_segments.admin
    :members:

apps.py
=======

.. automodule:: django_segments.apps
    :members:

app_settings.py
===============

Package settings.

.. data:: DJANGO_SEGMENTS_MODEL_BASE

    Base model for all segment and span models. Default is :class:`django.db.models.base.ModelBase`. There should be no need to change this, but it is provided for advanced users.

.. data:: POSTGRES_RANGE_FIELDS

    Dictionary of model range fields and the associated Python types that should be used to represent a boundary value, a delta value, and a range. Default is:

    .. code-block:: python

        {
            IntegerRangeField: {
                "value_type": int,
                "delta_type": int,
                "range_type": NumericRange,
            },
            BigIntegerRangeField: {
                "value_type": int,
                "delta_type": int,
                "range_type": NumericRange,
            },
            DecimalRangeField: {
                "value_type": Decimal,
                "delta_type": Decimal,
                "range_type": NumericRange,
            },
            DateRangeField: {
                "value_type": date,
                "delta_type": timezone.timedelta,
                "range_type": DateRange,
            },
            DateTimeRangeField: {
                "value_type": datetime,
                "delta_type": timezone.timedelta,
                "range_type": DateTimeTZRange,
            }
        }

    This is used to convert the range field to a Python type, and for validation when creating a new Span or Segment.

.. data:: DEFAULT_RELATED_NAME

    Default related name for the Span and Segment models. Default is ``%(app_label)s_%(class)s_related``.

.. data:: DEFAULT_RELATED_QUERY_NAME

    Default related query name for the Span and Segment models. Default is ``%(app_label)s_%(class)ss``.

Global Span Configuration Options
---------------------------------

These options are used to configure the behavior of all Span models, and can be overridden on a per-model basis by adding a ``SpanConfig`` class with one or more of the corresponding setting names in lowercase to the span model. Example:

.. code-block:: python

    class MySpan(AbstractSpan):

        class SpanConfig:
            """Custom configuration options for this span."""

            allow_span_gaps = False
            allow_segment_gaps = False
            soft_delete = False

.. data:: ALLOW_SPAN_GAPS

        Allow gaps between the boundaries of the Span and its first and last Segments. Default is ``True``. If ``False``, when a new Span is created, a Segment will be created to fill the range of the Span.

.. data:: ALLOW_SEGMENT_GAPS

        Allow gaps between the Segments in a Span. Default is ``True``. If ``False``, all Segments in a Span must be contiguous.

.. data:: SOFT_DELETE

        Use soft delete for segments and spans. Default is ``True``. If ``True``, a ``deleted_at`` field will be added to the Span and Segment models. When a soft delete occurs, the ``deleted_at`` field will be set to the current date and time, and queries will exclude deleted Segments and Spans by default.

Global Segment Configuration Options
------------------------------------

These options are used to configure the behavior of all Segment models, and can be overridden on a per-model basis by adding a ``SegmentConfig`` class with one or
more of the corresponding setting names in lowercase to the segment model. Example:

.. code-block:: python

    class MySegment(AbstractSegment):

        class SegmentConfig:
            """Custom configuration options for this segment."""

            previous_field_on_delete = models.CASCADE
            span_on_delete = models.CASCADE

.. data:: PREVIOUS_FIELD_ON_DELETE

    The behavior to use when deleting a segment that has a previous segment. Default is :attr:`django.db.models.CASCADE`.

-- data:: SPAN_ON_DELETE

    The behavior to use for segment instances with foreign key to a deleted span. Default is :attr:`django.db.models.CASCADE`.



exceptions.py
=============

.. automodule:: django_segments.exceptions
    :members:

forms.py
========

.. automodule:: django_segments.forms
    :members:

models/base.py
==============

.. automodule:: django_segments.models.base
    :members:

.. autoclass:: django_segments.models.base.BaseSpanMetaclass
   :members:
   :no-index:
   :special-members: __new__

.. autoclass:: django_segments.models.base.BaseSegmentMetaclass
   :members:
   :no-index:
   :special-members: __new__

models/segment.py
=================

.. automodule:: django_segments.models.segment
    :members:

models/span.py
==============

.. automodule:: django_segments.models.span
    :members:

signals.py
==========

.. automodule:: django_segments.signals
    :members:

When deleting or soft deleting a span, several signals are sent as the Span and its associated Segments are deleted. In each case, the more specific signal is wrapped in the more general signal. This allows you to connect to the more general signal and still receive the more specific signal. The signals are sent in the following order:

.. image:: https://raw.githubusercontent.com/OmenApps/django-segments/main/docs/media/signals-delete.png
    :alt: Signal Order
    :align: center


views.py
========

.. automodule:: django_segments.views
    :members:

urls.py
=======

.. automodule:: django_segments.urls
    :members:
```
