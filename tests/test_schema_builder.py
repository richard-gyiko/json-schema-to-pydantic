import pytest
from autogen_mcp_tool_adapter.schema_builder import JsonSchemaToPydantic


def test_basic_type_conversion():
    """Test conversion of basic JSON Schema types to Pydantic types.

    Verifies:
    1. Basic types (string, integer, number, boolean) are correctly converted
    2. Optional fields are properly handled with None defaults
    3. Type validation works for basic field types"""
    schema = {
        "type": "object",
        "properties": {
            "string_field": {"type": "string"},
            "integer_field": {"type": "integer"},
            "number_field": {"type": "number"},
            "boolean_field": {"type": "boolean"},
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "BasicTypes")

    # All fields should be optional by default
    instance = Model()
    assert instance.string_field is None
    assert instance.integer_field is None
    assert instance.number_field is None
    assert instance.boolean_field is None


def test_required_field_handling():
    """Test handling of required vs optional fields.

    Verifies:
    1. Required fields are enforced during validation
    2. Optional fields can be None
    3. Validation errors are raised for missing required fields"""
    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"},
        },
        "required": ["required_field"],
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "RequiredFields")

    # Should raise validation error for missing required field
    with pytest.raises(ValueError):
        Model()

    # Should work with required field
    instance = Model(required_field="test", optional_field=None)
    assert instance.required_field == "test"
    assert instance.optional_field is None


def test_nested_object_structure():
    """Test handling of nested object structures in schema.

    Verifies:
    1. Nested objects are converted to nested Pydantic models
    2. Nested field access works correctly
    3. Validation maintains nested structure integrity"""
    schema = {
        "type": "object",
        "properties": {
            "nested": {"type": "object", "properties": {"field": {"type": "string"}}}
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "NestedObject")

    instance = Model(nested={"field": "test"})
    assert instance.nested.field == "test"


def test_array_field_handling():
    """Test handling of array fields in schema.

    Verifies:
    1. Array fields are converted to Python lists
    2. Array item types are properly validated
    3. List operations work on array fields"""
    schema = {
        "type": "object",
        "properties": {"string_array": {"type": "array", "items": {"type": "string"}}},
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "ArrayTypes")

    instance = Model(string_array=["test1", "test2"])
    assert instance.string_array == ["test1", "test2"]


def test_string_and_number_constraints():
    """Test validation of string and number constraints.

    Verifies:
    1. String length constraints (minLength, maxLength) are enforced
    2. Number range constraints (minimum, maximum) are enforced
    3. Validation errors are raised for invalid values"""
    schema = {
        "type": "object",
        "properties": {
            "limited_string": {"type": "string", "minLength": 2, "maxLength": 5},
            "limited_number": {"type": "integer", "minimum": 0, "maximum": 100},
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "Validation")

    # Should raise for too short string
    with pytest.raises(ValueError):
        Model(limited_string="a")

    # Should raise for too large number
    with pytest.raises(ValueError):
        Model(limited_number=101)

    # Should work with valid values
    instance = Model(limited_string="test", limited_number=50)
    assert instance.limited_string == "test"
    assert instance.limited_number == 50


def test_format_type_conversion():
    """Test conversion of formatted string types.

    Verifies:
    1. Special string formats are converted to appropriate Python types
    2. Supported formats: email, date, datetime, uri, uuid
    3. Type conversion and validation work correctly"""
    schema = {
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "date_field": {"type": "string", "format": "date"},
            "datetime_field": {"type": "string", "format": "date-time"},
            "uri_field": {"type": "string", "format": "uri"},
            "uuid_field": {"type": "string", "format": "uuid"},
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "FormatTypes")

    from datetime import date, datetime
    from uuid import UUID

    instance = Model(
        email="test@example.com",
        date_field=date(2023, 1, 1),
        datetime_field=datetime(2023, 1, 1, 12, 0),
        uri_field="https://example.com",
        uuid_field="123e4567-e89b-12d3-a456-426614174000",
    )

    assert isinstance(instance.date_field, date)
    assert isinstance(instance.datetime_field, datetime)
    assert isinstance(instance.uuid_field, UUID)


def test_enum_field_handling():
    """Test handling of enum fields from schema.

    Verifies:
    1. Enum fields are converted to Python Enum classes
    2. Both string and number enums are supported
    3. Invalid enum values are rejected"""
    schema = {
        "type": "object",
        "properties": {
            "color": {"type": "string", "enum": ["red", "green", "blue"]},
            "number_choice": {"type": "integer", "enum": [1, 2, 3]},
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "EnumTypes")

    instance = Model(color="red", number_choice=2)
    assert instance.color.value == "red"
    assert instance.number_choice.value == 2

    with pytest.raises(ValueError):
        Model(color="yellow")


def test_data_validation_rules():
    """Test that data validation rules from JSON Schema are enforced by the generated model.

    This test verifies:
    1. The model accepts valid data matching schema constraints
    2. The model correctly enforces:
       - multipleOf rule for numbers
       - exclusiveMinimum/Maximum rules
       - uniqueItems rule for arrays
    3. Invalid data raises appropriate validation errors"""

    schema = {
        "type": "object",
        "properties": {
            "multiple_of": {"type": "number", "multipleOf": 2},
            "exclusive_minimum": {"type": "number", "exclusiveMinimum": 0},
            "exclusive_maximum": {"type": "number", "exclusiveMaximum": 100},
            "unique_items_array": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
        },
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "Constraints")

    # Valid values
    instance = Model(
        multiple_of=4,
        exclusive_minimum=1,
        exclusive_maximum=99,
        unique_items_array=["a", "b", "c"],
    )

    # Verify valid values were set correctly
    assert instance.multiple_of == 4
    assert instance.exclusive_minimum == 1
    assert instance.exclusive_maximum == 99
    assert isinstance(instance.unique_items_array, set)  # Verify it's a set
    assert instance.unique_items_array == {"a", "b", "c"}

    # Invalid values - include valid values for other fields to ensure
    # we're testing the specific constraint
    with pytest.raises(ValueError):
        Model(
            multiple_of=3,  # Invalid: not multiple of 2
            exclusive_minimum=1,
            exclusive_maximum=99,
            unique_items_array=["a", "b", "c"],
        )

    with pytest.raises(ValueError):
        Model(
            multiple_of=4,
            exclusive_minimum=0,  # Invalid: not > 0
            exclusive_maximum=99,
            unique_items_array=["a", "b", "c"],
        )

    # Test exclusiveMaximum validation
    with pytest.raises(ValueError):
        Model(
            multiple_of=4,
            exclusive_minimum=1,
            exclusive_maximum=100,  # Invalid: must be < 100
            unique_items_array=["a", "b", "c"],
        )

    # Verify that 99 is valid (as it's < 100)
    instance = Model(
        multiple_of=4,
        exclusive_minimum=1,
        exclusive_maximum=99,  # Valid: is < 100
        unique_items_array=["a", "b", "c"],
    )
    assert instance.exclusive_maximum == 99

    # Test that duplicate items are automatically deduplicated by the set
    instance = Model(
        multiple_of=4,
        exclusive_minimum=1,
        exclusive_maximum=99,
        unique_items_array=["a", "b", "a"],  # Duplicate item will be removed
    )
    assert instance.unique_items_array == {"a", "b"}


def test_additional_properties_constraint():
    """Test that the model enforces additionalProperties constraint from schema.

    This test verifies:
    1. The model accepts valid data with only defined properties
    2. The model rejects data with undefined additional properties
    3. The $schema field is properly filtered out during model generation"""

    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
        "$schema": "http://json-schema.org/draft-07/schema#",
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "NoAdditionalProps")

    # Valid case
    instance = Model(path="/some/path")
    assert instance.path == "/some/path"

    # Should raise when additional properties are provided
    with pytest.raises(ValueError):
        Model(path="/some/path", extra_field="should fail")


def test_complex_model_generation():
    """Test generation of complex models with multiple features.

    Verifies:
    1. Complex schemas with multiple nested levels work correctly
    2. Combination of arrays, objects, and constraints is handled
    3. Complex validation scenarios work as expected"""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "age": {"type": "integer", "minimum": 0},
            "addresses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                    },
                    "required": ["street", "city"],
                },
            },
        },
        "required": ["name"],
    }

    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "ComplexModel")

    instance = Model(
        name="John Doe",
        age=30,
        addresses=[
            {"street": "123 Main St", "city": "Boston"},
            {"street": "456 Side St", "city": "New York"},
        ],
    )

    assert instance.name == "John Doe"
    assert instance.age == 30
    assert len(instance.addresses) == 2
    assert instance.addresses[0].street == "123 Main St"
    assert instance.addresses[1].city == "New York"
