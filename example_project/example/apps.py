"""Example app config."""

import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ExampleConfig(AppConfig):
    """Example app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "example_project.example"

    def ready(self):
        logger.debug("Initializing example app")
