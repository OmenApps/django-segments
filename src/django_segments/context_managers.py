import logging

from django_segments.models.base import (
    BaseSegmentMetaclass,
    SegmentConfigurationHelper,
    boundary_helper_factory,
)

from .signals import (
    segment_create_failed,
    segment_delete_failed,
    segment_post_create,
    segment_post_delete,
    segment_post_delete_or_soft_delete,
    segment_post_soft_delete,
    segment_post_update,
    segment_pre_create,
    segment_pre_delete,
    segment_pre_delete_or_soft_delete,
    segment_pre_soft_delete,
    segment_pre_update,
    segment_update_failed,
    span_create_failed,
    span_delete_failed,
    span_post_create,
    span_post_delete,
    span_post_delete_or_soft_delete,
    span_post_soft_delete,
    span_post_update,
    span_pre_create,
    span_pre_delete,
    span_pre_delete_or_soft_delete,
    span_pre_soft_delete,
    span_pre_update,
    span_update_failed,
)


logger = logging.getLogger(__name__)


class SpanCreateSignalContext:
    """Context manager for sending signals before and after creating a span.

    Usage:

    .. code-block:: python

        with SpanCreateSignalContext(span_model, span_range) as context:
            span = Span.objects.create(span_range=span_range)
            context.kwargs["span"] = span
    """

    def __init__(self, span_model, span_range, *args, **kwargs):
        self.span_model = span_model
        self.span_range = span_range
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        span_pre_create.send(sender=self.span_model, span_range=self.span_range)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if (span := self.kwargs.get("span")) is not None:
                span_post_create.send(sender=self.span_model, span_range=self.span_range, span=span)
            else:
                print("Span instance not found in kwargs. Cannot send post create signal.")
            return

        print("Span creation failed for %s with range %s" % (self.span_model, self.span_range))  # pylint: disable=C0209
        span_create_failed.send(sender=self.span_model, span_range=self.span_range)


class SpanUpdateSignalContext:
    """Context manager for sending signals before and after updating a span.

    Usage:

    .. code-block:: python

        with SpanUpdateSignalContext(span):
            span.save()
    """

    def __init__(self, span, *args, **kwargs):
        self.span = span
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        span_pre_update.send(sender=self.span.__class__, span=self.span)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            span_post_update.send(sender=self.span.__class__, span=self.span)
            return

        print(
            "Span update failed for %s with exception %s, %s, %s"  # pylint: disable=C0209
            % (self.span, exc_type, exc_value, traceback)
        )
        span_update_failed.send(sender=self.span.__class__, span=self.span)


class SpanDeleteSignalContext:
    """Context manager for sending signals before and after deleting a span.

    Usage:

    .. code-block:: python

        with SpanDeleteSignalContext(span):
            span.delete()
    """

    def __init__(self, span, *args, **kwargs):
        self.span = span
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        span_pre_delete_or_soft_delete.send(sender=self.span.__class__, span=self.span)
        span_pre_delete.send(sender=self.span.__class__, span=self.span)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            span_post_delete.send(sender=self.span.__class__, span=self.span)
            span_post_delete_or_soft_delete.send(sender=self.span.__class__, span=self.span)
            return

        print("Span deletion failed for %s" % (self.span,))  # pylint: disable=C0209
        span_delete_failed.send(sender=self.span.__class__, span=self.span)


class SpanSoftDeleteSignalContext:
    """Context manager for sending signals before and after soft deleting a span.

    Usage:

    .. code-block:: python

        with SpanSoftDeleteSignalContext(span):
            span.soft_delete()
    """

    def __init__(self, span, *args, **kwargs):
        self.span = span
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        span_pre_delete_or_soft_delete.send(sender=self.span.__class__, span=self.span)
        span_pre_soft_delete.send(sender=self.span.__class__, span=self.span)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            span_post_soft_delete.send(sender=self.span.__class__, span=self.span)
            span_post_delete_or_soft_delete.send(sender=self.span.__class__, span=self.span)
            return

        print("Span soft deletion failed for %s" % (self.span,))  # pylint: disable=C0209
        span_delete_failed.send(sender=self.span.__class__, span=self.span)


class SegmentCreateSignalContext:
    """Context manager for sending signals before and after creating a segment.

    Usage:

    .. code-block:: python

        with SegmentCreateSignalContext(span, segment_range) as context:
            segment = Segment.objects.create(span=span, segment_range=segment_range)
            context.kwargs["segment"] = segment
    """

    def __init__(self, span, segment_range, *args, **kwargs):
        self.span = span
        self.segment_range = segment_range
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        segment_pre_create.send(sender=self.span.__class__, span=self.span, segment_range=self.segment_range)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if (segment := self.kwargs.get("segment")) is not None:
                segment_post_create.send(
                    sender=segment.__class__, span=self.span, segment=segment, segment_range=self.segment_range
                )
            else:
                print("Segment instance not found in kwargs. Cannot send post create signal.")
            return

        print("Segment creation failed for %s with range %s" % (self.span, self.segment_range))  # pylint: disable=C0209
        segment_create_failed.send(sender=self.span.__class__, span=self.span, segment_range=self.segment_range)


class SegmentUpdateSignalContext:
    """Context manager for sending signals before and after updating a segment.

    Usage:

    .. code-block:: python

        with SegmentUpdateSignalContext(segment):
            segment.save()
    """

    def __init__(self, segment, *args, **kwargs):
        self.segment = segment
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        segment_pre_update.send(sender=self.segment.__class__, segment=self.segment)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            segment_post_update.send(sender=self.segment.__class__, segment=self.segment)
            return

        print("Segment update failed for %s" % (self.segment,))  # pylint: disable=C0209
        segment_update_failed.send(sender=self.segment.__class__, segment=self.segment)


class SegmentDeleteSignalContext:
    """Context manager for sending signals before and after deleting a segment.

    Usage:

    .. code-block:: python

        with SegmentDeleteSignalContext(segment):
            segment.delete()
    """

    def __init__(self, segment, *args, **kwargs):
        self.segment = segment
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        segment_pre_delete_or_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
        segment_pre_delete.send(sender=self.segment.__class__, segment=self.segment)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            segment_post_delete.send(sender=self.segment.__class__, segment=self.segment)
            segment_post_delete_or_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
            return

        print("Segment deletion failed for %s" % (self.segment,))  # pylint: disable=C0209
        segment_delete_failed.send(sender=self.segment.__class__, segment=self.segment)


class SegmentSoftDeleteSignalContext:
    """Context manager for sending signals before and after soft deleting a segment.

    Usage:

    .. code-block:: python

        with SegmentSoftDeleteSignalContext(segment):
            segment.soft_delete()
    """

    def __init__(self, segment, *args, **kwargs):
        self.segment = segment
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        segment_pre_delete_or_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
        segment_pre_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            segment_post_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
            segment_post_delete_or_soft_delete.send(sender=self.segment.__class__, segment=self.segment)
            return

        print("Segment soft deletion failed for %s" % (self.segment,))  # pylint: disable=C0209
        segment_delete_failed.send(sender=self.segment.__class__, segment=self.segment)
