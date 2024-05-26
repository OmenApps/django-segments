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

    Dictionary of field name and Python type that should be used to represent the range field. Default is:

    .. code-block:: python

        {
            IntegerRangeField.__name__: int,
            BigIntegerRangeField.__name__: int,
            DecimalRangeField.__name__: float,
            DateRangeField.__name__: datetime.date,
            DateTimeRangeField.__name__: datetime,
        }

    This is used to convert the range field to a Python type when using the :meth:`django_segments.models.base.AbstractSpanMetaclass.get_range_field` method.

.. data:: ON_DELETE_FOR_PREVIOUS

    The behavior to use when deleting a segment or span that has a previous segment or span. Default is :attr:`django.db.models.CASCADE`.

Global Span Configuration Options
---------------------------------

These options are used to configure the behavior of all Span models, and can be overridden on a per-model basis by adding a ``Config`` class with one or more of the corresponding setting names in lowercase to the span model. Example:

.. code-block:: python

    class MySpan(AbstractSpan):

        class Config:
            """Custom configuration options for this span."""

            allow_gaps = False
            soft_delete = False

.. data:: ALLOW_GAPS

        Allow gaps between segments in a span. Default is ``True``.

.. data:: STICKY_BOUNDARIES

        Force spans & segments to have sticky boundaries (if a range boundary for a span or segment is the same as another segment or the encompassing span, any changes to the boundary are proparated to the objects sharing that boundary). Default is ``True``.

.. data:: SOFT_DELETE

        Use soft delete for segments and spans. Default is ``True``.

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

.. autoclass:: django_segments.models.base.AbstractSpanMetaclass
   :members:
   :no-index:
   :special-members: __new__

.. autoclass:: django_segments.models.base.AbstractSegmentMetaclass
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

views.py
========

.. automodule:: django_segments.views
    :members:

urls.py
=======

.. automodule:: django_segments.urls
    :members:
```
