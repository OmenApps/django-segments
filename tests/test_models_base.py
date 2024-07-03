from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.postgres.fields import (
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    IntegerRangeField,
)
from django.db import models, transaction
from django.db.utils import DataError
from django.test import TestCase
from django.utils import timezone
from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange

from django_segments.exceptions import (
    IncorrectRangeTypeError,
    IncorrectSubclassError,
    InvalidRangeFieldNameError,
)
from django_segments.models import AbstractSegment, AbstractSpan
from django_segments.models.base import (
    BaseSegmentMetaclass,
    BaseSpanMetaclass,
    ConcreteModelValidationHelper,
    SegmentConfigurationHelper,
    SpanConfigurationHelper,
    boundary_helper_factory,
)
from tests.example.models import (
    ConcreteBigIntegerSegment,
    ConcreteBigIntegerSpan,
    ConcreteDateSegment,
    ConcreteDateSpan,
    ConcreteDateTimeSegment,
    ConcreteDateTimeSpan,
    ConcreteDecimalSegment,
    ConcreteDecimalSpan,
    ConcreteIntegerSegment,
    ConcreteIntegerSpan,
    EventSegment,
    EventSpan,
)


@pytest.fixture
def mock_span_model():
    """Fixture for creating a mock model."""

    class MockModel(AbstractSpan):  # pylint: disable=R0903
        """Mock model for testing."""

        class SpanConfig:  # pylint: disable=C0115 disable=R0903
            range_field_type = IntegerRangeField

        class Meta:  # pylint: disable=C0115 disable=R0903
            app_label = "example"

    return MockModel()


@pytest.fixture
def mock_span_model_instance(mock_span_model):  # pylint: disable=W0621
    """Fixture for creating a mock model instance."""
    mock_span_model._meta.abstract = False  # pylint: disable=W0212
    return mock_span_model


@pytest.fixture
def concrete_integer_span():
    """Fixture for creating a concrete integer span."""
    return ConcreteIntegerSpan.objects.create(initial_range=NumericRange(0, 10), current_range=NumericRange(0, 10))


@pytest.fixture
def concrete_integer_segment(concrete_integer_span):  # pylint: disable=W0621
    """Fixture for creating a concrete integer segment."""
    return ConcreteIntegerSegment.objects.create(span=concrete_integer_span, segment_range=NumericRange(0, 10))


@pytest.fixture
def concrete_decimal_span():
    """Fixture for creating a concrete decimal span."""
    return ConcreteDecimalSpan.objects.create(
        initial_range=NumericRange(Decimal("0.0"), Decimal("10.0")),
        current_range=NumericRange(Decimal("0.0"), Decimal("10.0")),
    )


@pytest.fixture
def concrete_decimal_segment(concrete_decimal_span):  # pylint: disable=W0621
    """Fixture for creating a concrete decimal segment."""
    return ConcreteDecimalSegment.objects.create(
        span=concrete_decimal_span, segment_range=NumericRange(Decimal("0.0"), Decimal("10.0"))
    )


@pytest.fixture
def mock_segment_model():
    """Fixture for creating a mock segment model."""

    class MockSegmentModel(models.Model):  # pylint: disable=R0903
        """Mock segment model for testing."""

        segment_range = models.IntegerField()
        _meta = type("Meta", (object,), {"abstract": False})

        class SegmentConfig:  # pylint: disable=C0115 disable=R0903
            span_model = ConcreteIntegerSpan

    return MockSegmentModel()


@pytest.fixture
def abstract_span_test():
    """Fixture for creating an abstract span model."""

    class TestSpan(metaclass=BaseSpanMetaclass):  # pylint: disable=R0903
        """Abstract span model for testing."""

        class Meta:  # pylint: disable=C0115 disable=R0903
            abstract = True

        class SpanConfig:  # pylint: disable=C0115 disable=R0903
            range_field_type = DateTimeTZRange

    return TestSpan


@pytest.fixture
def abstract_segment_test():
    """Fixture for creating an abstract segment model."""

    class TestSegment(models.Model, metaclass=BaseSegmentMetaclass):  # pylint: disable=R0903
        """Abstract segment model for testing."""

        class Meta:  # pylint: disable=C0115 disable=R0903
            abstract = True

        class SpanConfig:  # pylint: disable=C0115 disable=R0903
            span_model = ConcreteIntegerSpan

    return TestSegment


@pytest.mark.django_db
class TestBoundaryHelperFactory:
    """Tests for the boundary_helper_factory function."""

    def test_set_lower_boundary(self, concrete_integer_span):  # pylint: disable=W0621
        """Test setting the lower boundary on a model instance."""
        set_lower_boundary, set_upper_boundary = boundary_helper_factory("current_range")  # pylint: disable=W0612

        assert concrete_integer_span.current_range.lower == 0

        concrete_integer_span.set_lower_boundary(2)
        assert concrete_integer_span.current_range.lower == 2

        set_lower_boundary(concrete_integer_span, 5)
        assert concrete_integer_span.current_range.lower == 5

    def test_set_upper_boundary(self, concrete_integer_span):  # pylint: disable=W0621
        """Test setting the upper boundary on a model instance."""
        set_lower_boundary, set_upper_boundary = boundary_helper_factory("current_range")  # pylint: disable=W0612

        assert concrete_integer_span.current_range.upper == 10

        concrete_integer_span.set_upper_boundary(8)
        assert concrete_integer_span.current_range.upper == 8

        set_upper_boundary(concrete_integer_span, 5)
        assert concrete_integer_span.current_range.upper == 5

    def test_wrong_range_field_type_for_validate_value_type(self):
        """Test that an error is raised when the range field type is incorrect."""

        with pytest.raises(IncorrectRangeTypeError):

            class WrongRangeTypeMockModel1(AbstractSpan):  # pylint: disable=R0903  disable=W0612
                """Mock model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = "ABC"

        with pytest.raises(IncorrectRangeTypeError):

            class TestClass:  # pylint: disable=R0903
                """Mock class for testing the range field type."""

            class WrongRangeTypeMockModel2(AbstractSpan):  # pylint: disable=R0903  disable=W0612
                """Mock model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = TestClass

    def test_invalid_field_name(self, concrete_integer_span):  # pylint: disable=W0621
        """Test setting a non-existent boundary field on a model."""
        set_lower_boundary, set_upper_boundary = boundary_helper_factory("non_existent_field")

        with pytest.raises(InvalidRangeFieldNameError):
            set_lower_boundary(concrete_integer_span, 5)

        with pytest.raises(InvalidRangeFieldNameError):
            set_upper_boundary(concrete_integer_span, 15)

    def test_invalid_value_type(self, concrete_integer_span):  # pylint: disable=W0621
        """Test that an error is raised for an invalid boundary value type."""
        set_lower_boundary, set_upper_boundary = boundary_helper_factory("current_range")

        with pytest.raises(ValueError):
            set_lower_boundary(concrete_integer_span, Decimal("5.0"))

        with pytest.raises(ValueError):
            set_upper_boundary(concrete_integer_span, "string_value")

    def test_valid_range_field_class(self, concrete_integer_span):  # pylint: disable=W0621
        """Test valid range field classes."""
        assert concrete_integer_span.current_range.lower == 0
        assert concrete_integer_span.current_range.upper == 10

        set_lower_boundary, set_upper_boundary = boundary_helper_factory("current_range")
        set_lower_boundary(concrete_integer_span, 3)
        set_upper_boundary(concrete_integer_span, 7)

        assert concrete_integer_span.current_range.lower == 3
        assert concrete_integer_span.current_range.upper == 7


@pytest.mark.django_db
class TestConcreteModelValidationHelper:  # pylint: disable=R0903
    """Tests for the ConcreteModelValidationHelper class."""

    def test_check_model_is_concrete(self, mock_span_model_instance):  # pylint: disable=W0621
        """Test that the check_model_is_concrete instance method works correctly."""
        ConcreteModelValidationHelper.check_model_is_concrete(mock_span_model_instance)

        with pytest.raises(IncorrectSubclassError):
            mock_span_model = mock_span_model_instance.__class__  # pylint: disable=W0621

            class AbstractSpan(mock_span_model):  # pylint: disable=W0621 disable=C0115 disable=R0903
                class Meta:  # pylint: disable=C0115 disable=R0903
                    abstract = True

            ConcreteModelValidationHelper.check_model_is_concrete(AbstractSpan)

    def test_get_config_attr_error(self, mock_span_model_instance):  # pylint: disable=W0621  disable=W0613
        """Test getting a configuration attribute from a span model with no SpanConfig."""
        with pytest.raises(IncorrectSubclassError):

            class InvalidSpanConfigMockModel:  # pylint: disable=R0903 disable=W0612
                """Mock model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

            mock_invalid_span_config_model = InvalidSpanConfigMockModel()

            SpanConfigurationHelper.get_config_attr(mock_invalid_span_config_model, "non_existing_attr", None)

    def test_get_range_field_type_error(self, mock_span_model_instance):  # pylint: disable=W0621 disable=W0613
        """Test the error raised for incorrect range field type in span model."""
        with pytest.raises(IncorrectRangeTypeError):

            class InvalidRangeFieldTypeMockModel:
                """Mock model for testing."""

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = "InvalidRangeType"

            SpanConfigurationHelper.get_range_field_type(InvalidRangeFieldTypeMockModel)

    def test_get_segment_class(self, concrete_integer_span):  # pylint: disable=W0621
        """Test retrieving the segment class from the span model."""
        assert SpanConfigurationHelper.get_segment_class(concrete_integer_span) == ConcreteIntegerSegment

    def test_segment_class_not_found(self, mock_span_model_instance):  # pylint: disable=W0621 disable=W0613
        """Test retrieving a segment class when it does not exist for span model."""
        with pytest.raises(IndexError):

            class MockModelWithoutSegments(models.Model):
                """Mock model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = IntegerRangeField

            SpanConfigurationHelper.get_segment_class(MockModelWithoutSegments)


@pytest.mark.django_db
class TestBaseSpanMetaclass:  # pylint: disable=R0903
    """Tests related to the BaseSpanMetaclass."""

    def test_metaclass_incorrect_application(self):
        """Test incorrect application of BaseSpanMetaclass leading to error."""
        with pytest.raises(IncorrectSubclassError):

            class InvalidModel(metaclass=BaseSpanMetaclass):  # pylint: disable=W0612 disable=R0903
                """Invalid model for testing."""


@pytest.mark.django_db
class TestBaseSegmentMetaclass:  # pylint: disable=R0903
    """Tests related to BaseSegmentMetaclass."""

    def test_metaclass_incorrect_application(self):
        """Test incorrect application of BaseSegmentMetaclass leading to error."""
        with pytest.raises(IncorrectSubclassError):

            class InvalidSegmentModel(metaclass=BaseSegmentMetaclass):  # pylint: disable=W0612 disable=R0903
                """Invalid segment model for testing."""


@pytest.mark.django_db
class TestSpanAndSegmentSoftDelete:
    """Tests for soft delete functionality in spans and segments."""

    def test_soft_delete_span(self, concrete_integer_span):  # pylint: disable=W0621
        """Test soft deleting a span."""
        assert concrete_integer_span.deleted_at is None

        # Soft delete the span
        concrete_integer_span.deleted_at = timezone.now()
        concrete_integer_span.save()

        assert concrete_integer_span.deleted_at is not None

    def test_soft_delete_segment(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test soft deleting a segment."""
        assert concrete_integer_segment.deleted_at is None

        # Soft delete the segment
        concrete_integer_segment.deleted_at = timezone.now()
        concrete_integer_segment.save()

        assert concrete_integer_segment.deleted_at is not None


@pytest.mark.django_db
class TestSpanMetaclassRangeFields:
    """Test the range fields configured by BaseSpanMetaclass."""

    def test_range_fields_in_metaclass(self, integer_span):  # pylint: disable=W0621
        """Ensure metaclass configures range fields properly."""
        assert hasattr(integer_span, "initial_range")
        assert hasattr(integer_span, "current_range")

    def test_index_on_range_fields(self, integer_span):  # pylint: disable=W0621
        """Ensure metaclass adds indexes to range fields."""
        model_meta_indexes = integer_span._meta.indexes  # pylint: disable=W0212

        assert any(index.fields == ["initial_range"] for index in model_meta_indexes)
        assert any(index.fields == ["current_range"] for index in model_meta_indexes)


@pytest.mark.django_db
class TestSegmentMetaclassRangeFields:
    """Test the range fields configured by BaseSegmentMetaclass."""

    def test_range_fields_in_metaclass(self, integer_segment):  # pylint: disable=W0621
        """Ensure metaclass configures range fields properly."""
        assert hasattr(integer_segment, "segment_range")

    def test_index_on_range_fields(self, integer_segment):  # pylint: disable=W0621
        """Ensure metaclass adds indexes to range fields."""
        model_meta_indexes = integer_segment._meta.indexes  # pylint: disable=W0212

        assert any(index.fields == ["segment_range"] for index in model_meta_indexes)


@pytest.mark.django_db
class TestSpanConfigurationHelper:
    """Tests for the SpanConfigurationHelper class."""

    def test_get_config_attr(self, integer_span):  # pylint: disable=W0621
        """Test getting a configuration attribute from a span model."""
        config_value = SpanConfigurationHelper.get_config_attr(integer_span, "allow_span_gaps", False)
        assert config_value is True

    def test_get_range_field_type(self, integer_span):  # pylint: disable=W0621
        """Test getting the range type from a span model."""
        range_field_type = SpanConfigurationHelper.get_range_field_type(integer_span)
        assert range_field_type.__name__ == "IntegerRangeField"

    @pytest.mark.parametrize(
        "model_fixture,expected_type",
        [
            ("integer_span", IntegerRangeField),
            ("big_integer_span", BigIntegerRangeField),
            ("decimal_span", DecimalRangeField),
            ("date_span", DateRangeField),
            ("datetime_span", DateTimeRangeField),
        ],
    )
    def test_span_configuration_range_field_type(self, model_fixture, expected_type, request):
        """Test that the range field type is correctly retrieved from a Span model."""
        span = request.getfixturevalue(model_fixture)
        range_field_type = SpanConfigurationHelper.get_range_field_type(span)
        assert range_field_type == expected_type

    def test_boundary_helper_factory_invalid_field(self, concrete_integer_span):  # pylint: disable=W0621
        """Test that an error is raised when trying to create a boundary helper for an invalid field."""
        with pytest.raises(InvalidRangeFieldNameError):
            _set_lower_boundary, _ = boundary_helper_factory("invalid_range_field")
            _set_lower_boundary(concrete_integer_span, 5)

    def test_config_attr_default_value(self, mock_span_model_instance):  # pylint: disable=W0621
        """Test that the default value is returned when the attribute does not exist."""
        default_value = "default"
        assert (
            SpanConfigurationHelper.get_config_attr(mock_span_model_instance, "non_existing_attr", default_value)
            == default_value
        )

    def test_set_boundary_atomic_transaction(self, date_span_and_segments):
        """Test that setting boundaries is atomic."""
        span, [segment1, segment2, segment3] = date_span_and_segments  # pylint: disable=W0612

        original_lower = span.current_range.lower
        # original_upper = segment3.segment_range.upper
        original_upper = span.current_range.upper

        print(f"{span.current_range=}, {segment1.segment_range=}, {segment2.segment_range=}, {segment3.segment_range=}")

        with pytest.raises(DataError):
            with transaction.atomic():
                segment3.set_upper_boundary(segment1.segment_range.lower)
                segment1.set_lower_boundary(segment1.segment_range.upper)
                segment1.save()
                segment3.save()

        span.refresh_from_db()
        assert span.current_range.lower == original_lower
        assert span.current_range.upper == original_upper

    def test_retrieve_segment_class(self, decimal_segment):
        """Test that the segment class can be retrieved from a segment model."""
        segment_class = SegmentConfigurationHelper.get_span_model(decimal_segment)
        assert issubclass(segment_class, AbstractSpan)

    def test_retrieve_segment_class_error(self):  # pylint: disable=W0621
        """Test that an error is raised when trying to retrieve the segment class from a non-segment model."""
        with pytest.raises(IncorrectSubclassError):
            SegmentConfigurationHelper.get_span_model(object())

    def test_manipulate_boundaries(self, concrete_decimal_segment):  # pylint: disable=W0621
        """Test that the boundaries can be manipulated on a Segment."""
        set_lower_boundary, set_upper_boundary = boundary_helper_factory("segment_range")

        set_lower_boundary(concrete_decimal_segment, Decimal("2.0"))
        set_upper_boundary(concrete_decimal_segment, Decimal("8.0"))

        assert concrete_decimal_segment.segment_range.lower == Decimal("2.0")
        assert concrete_decimal_segment.segment_range.upper == Decimal("8.0")

    @pytest.mark.parametrize(
        "span_fixture, initial_range, lower_value, upper_value",
        [
            (
                "integer_span",
                NumericRange(-2147483648, 2147483647),
                -2147483647,
                2147483646,
            ),
            (
                "big_integer_span",
                NumericRange(-9223372036854775808, 9223372036854775807),
                -9223372036854775807,
                9223372036854775806,
            ),
            (
                "decimal_span",
                NumericRange(Decimal("-10.0"), Decimal("10.0")),
                Decimal("-9.0"),
                Decimal("9.0"),
            ),
            (
                "date_span",
                DateRange(timezone.now().date(), (timezone.now() + timedelta(days=10)).date()),
                timezone.now().date() + timedelta(days=1),
                (timezone.now() + timedelta(days=9)).date(),
            ),
            (
                "datetime_span",
                DateTimeTZRange(timezone.now(), timezone.now() + timedelta(days=10)),
                timezone.now() + timedelta(days=1),
                timezone.now() + timedelta(days=9),
            ),
        ],
    )
    def test_dynamic_range_helper_methods(self, span_fixture, initial_range, lower_value, upper_value, request):
        """Test that the dynamic range helper methods work as expected."""
        span = request.getfixturevalue(span_fixture)
        span.current_range = initial_range
        lower_boundary_setter, upper_boundary_setter = boundary_helper_factory("current_range")

        lower_boundary_setter(span, lower_value)
        upper_boundary_setter(span, upper_value)

        assert span.current_range.lower == lower_value
        assert span.current_range.upper == upper_value

    def test_span_add_field(self):
        """Test that a field can be added to a Span model."""

        class TestSpan(AbstractSpan):  # pylint: disable=R0903
            """Span with an additional field."""

            class Meta:  # pylint: disable=C0115 disable=R0903
                app_label = "example"

            class SpanConfig:  # pylint: disable=C0115 disable=R0903
                range_field_type = IntegerRangeField

            additional_field = models.IntegerField()

        assert hasattr(TestSpan, "additional_field")
        assert isinstance(TestSpan._meta.get_field("additional_field"), models.IntegerField)  # pylint: disable=W0212

    def test_span_helper_with_additional_fields(self):
        """Test that a Span can have additional fields added to it."""

        class AdditionalFieldSpan(AbstractSpan):  # pylint: disable=R0903
            """Span with an additional field."""

            class Meta:  # pylint: disable=C0115 disable=R0903
                app_label = "example"

            class SpanConfig:  # pylint: disable=C0115 disable=R0903
                range_field_type = IntegerRangeField

            additional_field = models.CharField(max_length=100)

        span = AdditionalFieldSpan()
        assert hasattr(span, "additional_field")
        assert isinstance(span._meta.get_field("additional_field"), models.CharField)  # pylint: disable=W0212

    def test_invalid_range_field_type_for_span(self):
        """Test that an invalid range type raises an IncorrectRangeTypeError when creating a Span."""
        with pytest.raises(IncorrectRangeTypeError):

            class InvalidSpan(AbstractSpan):  # pylint: disable=R0903
                """Span with an invalid range field type."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = None

            InvalidSpan()

    def test_get_config_dict_from_span(self, concrete_integer_span):  # pylint: disable=W0621
        """Test getting the configuration dictionary from a Span."""
        config_dict = SpanConfigurationHelper.get_config_dict(concrete_integer_span)
        assert isinstance(config_dict, dict)
        assert "allow_span_gaps" in config_dict
        assert "allow_segment_gaps" in config_dict
        assert "soft_delete" in config_dict
        assert config_dict["range_field_type"] is IntegerRangeField

    def test_set_boundaries_directly_on_span(self, date_span):
        """Test setting the boundaries directly on the Span."""
        date_span.set_initial_lower_boundary(timezone.now().date())
        date_span.set_initial_upper_boundary(timezone.now().date() + timedelta(days=10))

        assert date_span.initial_range.lower == timezone.now().date()
        assert date_span.initial_range.upper == timezone.now().date() + timedelta(days=10)


@pytest.mark.django_db
class TestSegmentConfigurationHelper:
    """Tests for the SegmentConfigurationHelper class."""

    def test_get_config_attr(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test getting a configuration attribute from a segment model."""
        config_value = SegmentConfigurationHelper.get_config_attr(concrete_integer_segment, "span_model", None)
        assert config_value.__name__ == "ConcreteIntegerSpan"

    def test_get_span_model(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test getting the span model from a segment model."""
        span_model = SegmentConfigurationHelper.get_span_model(concrete_integer_segment)
        assert span_model.__name__ == "ConcreteIntegerSpan"

    def test_get_span_model_error(self):
        """Test getting the span model from a model that does not have a span model."""

        class MockSegment:  # pylint: disable=R0903
            """Mock segment model for testing."""

            class SegmentConfig:  # pylint: disable=C0115 disable=R0903
                span_model = None

        with pytest.raises(IncorrectSubclassError):
            SegmentConfigurationHelper.get_span_model(MockSegment)


@pytest.mark.django_db
class TestAbstractModelCreation:
    """Tests for creating abstract models."""

    def test_create_abstract_span_raises_error(self):
        """Test that an error is raised when trying to create an instance of an abstract span model."""

        with pytest.raises(IncorrectSubclassError):

            class TestSpan(AbstractSpan):  # pylint: disable=R0903
                """Abstract span model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"
                    abstract = True

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = DateTimeRangeField

            TestSpan()

    def test_create_abstract_segment_raises_error(self, concrete_integer_span):  # pylint: disable=W0621
        """Test that an error is raised when trying to create an instance of an abstract segment model."""

        with pytest.raises(IncorrectSubclassError):

            class TestSegment(AbstractSegment):  # pylint: disable=R0903
                """Abstract segment model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"
                    abstract = True

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    span_model = concrete_integer_span

            TestSegment()

    def test_span_configuration_missing(self):
        """Test that an error is raised when the SpanConfig is missing."""

        with pytest.raises(IncorrectRangeTypeError):

            class TestSpanMissingConfig(AbstractSpan):  # pylint: disable=R0903
                """Abstract span model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"

            TestSpanMissingConfig()


@pytest.mark.django_db
class TestSpanAndSegmentCreation:
    """Tests for creating spans and segments."""

    def test_span_and_segment_creation(self, integer_span, integer_segment):
        """Test that a span and segment can be created and associated with each other."""
        span = integer_span
        segment = integer_segment

        assert span.initial_range == span.current_range
        assert segment.span == span

    def test_span_upper_lower_boundary(self, date_span):
        """Test that the upper and lower boundaries can be set on a span."""
        date_span.set_lower_boundary(timezone.now().date() - timedelta(days=1))
        date_span.set_upper_boundary((timezone.now() + timedelta(days=11)).date())
        assert date_span.current_range.lower == (timezone.now() - timedelta(days=1)).date()
        assert date_span.current_range.upper == (timezone.now() + timedelta(days=11)).date()


@pytest.mark.django_db
class TestBoundaryHelperFactoryValidation:
    """Tests for the ConcreteModelValidationHelper class."""

    def test_validate_value_type_concrete_model(self, mock_span_model_instance):  # pylint: disable=W0621
        """Test that the value type is validated correctly for a concrete model."""
        mock_field_name = "current_range"
        _, set_upper_boundary = boundary_helper_factory(mock_field_name)
        with pytest.raises(
            InvalidRangeFieldNameError,
            match=r"^Invalid range field name: current_range does not exist on MockModel object \(None\)$",
        ):
            set_upper_boundary(mock_span_model_instance, None)
        with pytest.raises(
            InvalidRangeFieldNameError,
            match=r"^Invalid range field name: current_range does not exist on MockModel object \(None\)$",
        ):
            set_upper_boundary(mock_span_model_instance, "invalid_type")

    def test_span_configuration_helper_fallback(self, concrete_integer_span):  # pylint: disable=W0621
        """Test that the default value is returned when the attribute does not exist."""
        default_value = False
        value = SpanConfigurationHelper.get_config_attr(concrete_integer_span, "non_existing_attr", default_value)
        assert value == default_value

    def test_segment_configuration_helper_fallback(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test that the default value is returned when the attribute does not exist."""
        default_value = True
        value = SegmentConfigurationHelper.get_config_attr(concrete_integer_segment, "non_existing_attr", default_value)
        assert value == default_value

    def test_span_configuration_valid_range_field_type(self, concrete_integer_span):  # pylint: disable=W0621
        """Test that the range type is correctly retrieved from a Span model."""
        range_field_type = SpanConfigurationHelper.get_range_field_type(concrete_integer_span)
        assert issubclass(range_field_type, IntegerRangeField)

    def test_segment_configuration_helper_get_span_model_class(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test that the span model class is retrieved from a segment model."""
        span_model = SegmentConfigurationHelper.get_span_model(concrete_integer_segment)
        assert issubclass(span_model, ConcreteIntegerSpan)

    def test_base_span_incorrect_base_for_metaclass(self):
        """Test that an error is raised when the class bases are incorrect."""
        with pytest.raises(IncorrectSubclassError):

            class TestSpanInvalidRangeType(metaclass=BaseSpanMetaclass):  # pylint: disable=R0903 disable=W0612
                """Invalid span model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    abstract = True

                class SpanConfig:  # pylint: disable=C0115 disable=R0903
                    range_field_type = "InvalidRangeType"

        with pytest.raises(IncorrectSubclassError):

            class TestSpanInvalidRangeTypeBase:  # pylint: disable=R0903
                """Invalid span model for testing."""

            class TestSegmentMissingSpanModel(
                TestSpanInvalidRangeTypeBase, metaclass=BaseSegmentMetaclass
            ):  # pylint: disable=R0903
                """Test segment model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"
                    abstract = False

                class SegmentConfig:  # pylint: disable=C0115 disable=R0903
                    span_model = None

            TestSegmentMissingSpanModel()

    def test_segment_range_field_addition(self, concrete_integer_segment):  # pylint: disable=W0621
        """Test that the segment range field is added to the segment model."""
        assert hasattr(concrete_integer_segment, "segment_range")
        assert concrete_integer_segment.segment_range == NumericRange(0, 10)

    def test_method_behavior_on_abstract_segment_model(self, abstract_segment_test):  # pylint: disable=W0621
        """Test that an error is raised when trying to create an instance of an abstract segment model."""
        with pytest.raises(IncorrectSubclassError):

            class TestSegment(abstract_segment_test):  # pylint: disable=R0903
                """Concrete segment model for testing."""

                class Meta:  # pylint: disable=C0115 disable=R0903
                    app_label = "example"
                    abstract = True

            TestSegment()

    def test_segment_configuration_non_existing_attr(self, concrete_decimal_segment):  # pylint: disable=W0621
        """Test that the correct default is returned when trying to get a non-existing attribute."""
        assert SegmentConfigurationHelper.get_config_attr(concrete_decimal_segment, "non_existing_attr", None) is None
        assert SegmentConfigurationHelper.get_config_attr(concrete_decimal_segment, "non_existing_attr", "XYZ") == "XYZ"

    def test_segment_configuration_missing_default(self, concrete_decimal_segment):  # pylint: disable=W0621
        """Test that a TypeError is raised if no default is provided for `get_config_attr`."""
        with pytest.raises(TypeError):
            SegmentConfigurationHelper.get_config_attr(concrete_decimal_segment, "non_existing_attr")
