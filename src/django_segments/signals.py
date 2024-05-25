import django.dispatch


span_created = django.dispatch.Signal(providing_args=["instance"])
segment_created = django.dispatch.Signal(providing_args=["instance"])
