"""Signals for the django_segments app.

Create

- `span_pre_create`: Sent before a span is created.
- `segment_pre_create`: Sent before a segment is created.
- `span_post_create`: Sent after a span is created.
- `segment_post_create`: Sent after a segment is created.

Pre Delete

- `segment_pre_delete`: Sent before a segment is deleted.
- `segment_pre_soft_delete`: Sent before a segment is soft deleted.
- `segment_pre_delete_or_soft_delete`: Sent before a segment is deleted or soft deleted.
- `span_pre_delete`: Sent before a span is deleted.
- `span_pre_soft_delete`: Sent before a span is soft deleted.
- `span_pre_delete_or_soft_delete`: Sent before a span is deleted or soft deleted.

Post Delete

- `segment_post_delete`: Sent after a segment is deleted.
- `segment_post_soft_delete`: Sent after a segment is soft deleted.
- `segment_post_delete_or_soft_delete`: Sent after a segment is deleted or soft deleted.
- `span_post_delete`: Sent after a span is deleted.
- `span_post_soft_delete`: Sent after a span is soft deleted.
- `span_post_delete_or_soft_delete`: Sent after a span is deleted or soft deleted.

Update

- `segment_pre_update`: Sent before a segment is updated.
- `segment_post_update`: Sent after a segment is updated.
- `span_pre_update`: Sent before a span is updated.
- `span_post_update`: Sent after a span is updated.

"""
import django.dispatch


# Create
span_pre_create = django.dispatch.Signal()
segment_pre_create = django.dispatch.Signal()
span_post_create = django.dispatch.Signal()
segment_post_create = django.dispatch.Signal()

# Pre Delete
segment_pre_delete = django.dispatch.Signal()
segment_pre_soft_delete = django.dispatch.Signal()
segment_pre_delete_or_soft_delete = django.dispatch.Signal()
span_pre_delete = django.dispatch.Signal()
span_pre_soft_delete = django.dispatch.Signal()
span_pre_delete_or_soft_delete = django.dispatch.Signal()

# Post Delete
segment_post_delete = django.dispatch.Signal()
segment_post_soft_delete = django.dispatch.Signal()
segment_post_delete_or_soft_delete = django.dispatch.Signal()
span_post_delete = django.dispatch.Signal()
span_post_soft_delete = django.dispatch.Signal()
span_post_delete_or_soft_delete = django.dispatch.Signal()

# Update
segment_pre_update = django.dispatch.Signal()
segment_post_update = django.dispatch.Signal()
span_pre_update = django.dispatch.Signal()
span_post_update = django.dispatch.Signal()
