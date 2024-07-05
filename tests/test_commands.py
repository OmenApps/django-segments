from typing import Any

import pytest
from django.apps import apps
from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models

from django_segments.management.commands.django_segments_models import Command
from django_segments.models import AbstractSegment, AbstractSpan


@pytest.mark.django_db
def test_django_segments_models_command(capfd):
    """Test the django_segments_models command."""
    call_command("django_segments_models")
    captured = capfd.readouterr()
    assert "Printing model fields for each model descending from AbstractSegment or AbstractSpan" in captured.out


@pytest.mark.django_db
def test_django_segments_models_command_error(mocker):
    """Test the django_segments_models command when an error occurs."""
    mocker.patch(
        "django_segments.management.commands.django_segments_models.Command.handle",
        side_effect=CommandError("Error occurred"),
    )
    with pytest.raises(CommandError) as excinfo:
        call_command("django_segments_models")
    assert "Error occurred" in str(excinfo.value)


@pytest.fixture
def mock_models(mocker):
    """Mock models that extend AbstractSegment or AbstractSpan."""

    class MockSpanModel(AbstractSpan):  # pylint: disable=R0903
        """Mock model that extends AbstractSpan."""

        class Meta:  # pylint: disable=C0115 disable=R0903
            app_label = "example"

        class SpanConfig:  # pylint: disable=C0115 disable=R0903
            range_field_type = IntegerRangeField

    class MockSegmentModel(AbstractSegment):  # pylint: disable=R0903
        """Mock model that extends AbstractSegment."""

        class Meta:  # pylint: disable=C0115 disable=R0903
            app_label = "example"

        class SegmentConfig:  # pylint: disable=C0115 disable=R0903
            span_model = MockSpanModel

    mocker.patch("django.apps.apps.get_models", return_value=[MockSpanModel, MockSegmentModel])
    return [MockSpanModel, MockSegmentModel]


@pytest.mark.django_db
def test_print_model_fields_command(capfd, mock_models):  # pylint: disable=W0613  disable=W0621
    """Test the print_model_fields command by checking the output."""

    call_command("django_segments_models")
    captured = capfd.readouterr()

    # Verify the output for MockSpanModel
    assert "Model: MockSpanModel" in captured.out
    assert "Model: MockSegmentModel" in captured.out
    assert "range_field_type_name: DateTimeField" in captured.out
    assert "null: True" in captured.out
    assert "blank: True" in captured.out
