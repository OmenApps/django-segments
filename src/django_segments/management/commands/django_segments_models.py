"""Prints the model fields in each model descending from AbstractSegment or AbstractSpan in the Django project."""

import logging
from typing import Any, Dict

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

from django_segments.models import AbstractSegment, AbstractSpan


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Prints details of model fields in each model descending from AbstractSegment or AbstractSpan in the project."""

    help = (
        "Prints details of model fields in each model descending from AbstractSegment or AbstractSpan in the project."
    )

    def handle(self, *args: Any, **options: Any) -> None:  # pylint: disable=W0613
        """Handle the command."""
        self.formatted("\nPrinting model fields for each model descending from AbstractSegment or AbstractSpan", "pink")
        self.formatted("====================================================================================", "pink")

        models_to_print = self.get_models_to_print()
        for model in models_to_print:
            self.print_model_fields(model)

    def get_models_to_print(self) -> list:
        """Get a list of models that are subclasses of AbstractSegment or AbstractSpan."""
        return [model for model in apps.get_models() if issubclass(model, (AbstractSegment, AbstractSpan))]

    def formatted(self, text: str, color: str, end: str = "\n") -> None:
        """Print the given text in the given color."""
        colors = {"green": "\x1b[32m", "yellow": "\x1b[33m", "blue": "\x1b[34m", "pink": "\x1b[35m"}
        reset = "\x1b[0m"
        self.stdout.write(colors.get(color, "") + text + reset + end)

    def print_model_fields(self, model: models.Model) -> None:
        """Print the model fields for the given model."""
        self.formatted(f"\nModel: {model.__name__}", "yellow")

        for field in model._meta.get_fields():  # pylint: disable=W0212
            self.print_field_details(field)

    def print_field_details(self, field: models.Field) -> None:
        """Print the details of the given field."""
        field_details = self.get_field_details(field)

        # if not (field_details["is_relation"] and field_details["related_name"] is None):
        #     self.formatted(f"\tField:  {field.name}", "blue")

        #     for key, value in field_details.items():
        #         if value is not None and key != "is_relation":
        #             self.formatted(f"\t\t{key}: {value}", "green")

        self.formatted(f"\tField:  {field.name}", "blue")

        for key, value in field_details.items():
            if value is not None and key != "is_relation":
                self.formatted(f"\t\t{key}: {value}", "green")

    def get_field_details(self, field: models.Field) -> Dict[str, Any]:
        """Get the details of the given field."""
        range_field_type = (
            field.get_internal_type() if not getattr(field, "one_to_many", False) else "Reverse of a ForeignKey"
        )

        return {
            "range_field_type": range_field_type,
            "null": getattr(field, "null", None),
            "blank": getattr(field, "blank", None),
            "default": self.get_field_default(field),
            "choices": getattr(field, "choices", None),
            "on_delete": getattr(field, "on_delete", None).__name__ if hasattr(field, "on_delete") else None,
            "related_model": getattr(field, "related_model", None).__name__
            if getattr(field, "related_model", None) is not None
            else None,
            "is_relation": getattr(field, "is_relation", None),
            "related_name": getattr(field, "_related_name", None),
            "related_query_name": getattr(field, "_related_query_name", None),
        }

    def get_field_default(self, field: models.Field) -> Any:
        """Get the default value of the field, if not set to NOT_PROVIDED."""
        default = getattr(field, "default", None)
        return default if default and not callable(default) else None
