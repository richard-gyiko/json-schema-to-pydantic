import pytest
from autogen_mcp_tool_adapter.schema_builder_1 import PydanticModelBuilder


def test_basic_type_conversion():
    """Test conversion of basic JSON Schema types to Pydantic types."""
    schema = {
        "type": "object",
        "properties": {
            "string_field": {"type": "string"},
            "integer_field": {"type": "integer"},
            "number_field": {"type": "number"},
            "boolean_field": {"type": "boolean"},
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    # All fields should be optional by default
    instance = Model()
    assert instance.string_field is None
    assert instance.integer_field is None
    assert instance.number_field is None
    assert instance.boolean_field is None


def test_required_field_handling():
    """Test handling of required vs optional fields."""
    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"},
        },
        "required": ["required_field"],
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    # Should raise validation error for missing required field
    with pytest.raises(ValueError):
        Model()

    # Should work with required field
    instance = Model(required_field="test", optional_field=None)
    assert instance.required_field == "test"
    assert instance.optional_field is None


def test_nested_object_structure():
    """Test handling of nested object structures in schema."""
    schema = {
        "type": "object",
        "properties": {
            "nested": {"type": "object", "properties": {"field": {"type": "string"}}}
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    instance = Model(nested={"field": "test"})
    assert instance.nested.field == "test"


def test_array_field_handling():
    """Test handling of array fields in schema."""
    schema = {
        "type": "object",
        "properties": {"string_array": {"type": "array", "items": {"type": "string"}}},
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    instance = Model(string_array=["test1", "test2"])
    assert instance.string_array == ["test1", "test2"]


def test_string_and_number_constraints():
    """Test validation of string and number constraints."""
    schema = {
        "type": "object",
        "properties": {
            "limited_string": {"type": "string", "minLength": 2, "maxLength": 5},
            "limited_number": {"type": "integer", "minimum": 0, "maximum": 100},
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

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


def test_anyof_handling():
    """Test handling of anyOf schema combinations."""
    schema = {
        "type": "object",
        "properties": {
            "flexible_field": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "number"},
                        },
                        "required": ["name", "value"],
                    },
                ]
            }
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    # Test string value
    instance = Model(flexible_field="test string")
    assert instance.flexible_field == "test string"

    # Test number value
    instance = Model(flexible_field=42.5)
    assert instance.flexible_field == 42.5

    # Test object value
    instance = Model(flexible_field={"name": "test", "value": 123})
    assert instance.flexible_field["name"] == "test"
    assert instance.flexible_field["value"] == 123

    # Should raise for invalid type
    with pytest.raises(ValueError):
        Model(flexible_field=True)  # Boolean is not one of the allowed types


def test_oneof_handling():
    """Test handling of oneOf schema combinations."""
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "code": {"type": "integer", "enum": [200, 201]},
                            "message": {"type": "string"},
                        },
                        "required": ["code", "message"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "details": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["error"],
                    },
                ]
            }
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    # Test success response
    instance = Model(status={"code": 200, "message": "Success"})
    assert instance.status["code"] == 200
    assert instance.status["message"] == "Success"

    # Test error response
    instance = Model(status={"error": "Not Found", "details": ["Resource missing"]})
    assert instance.status["error"] == "Not Found"
    assert instance.status["details"] == ["Resource missing"]

    # Should raise when neither schema matches
    with pytest.raises(ValueError):
        Model(status={"invalid": "data"})


def test_allof_handling():
    """Test handling of allOf schema combinations."""
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                        "required": ["id"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "active": {"type": "boolean"},
                        },
                        "required": ["email"],
                    },
                ]
            }
        },
    }

    builder = PydanticModelBuilder()
    Model = builder.create_pydantic_model(schema)

    # Test valid data meeting all constraints
    instance = Model(
        user={"id": 1, "name": "John Doe", "email": "john@example.com", "active": True}
    )
    assert instance.user["id"] == 1
    assert instance.user["name"] == "John Doe"
    assert instance.user["email"] == "john@example.com"
    assert instance.user["active"] is True

    # Should raise when required field from any schema is missing
    with pytest.raises(ValueError):
        Model(user={"id": 1, "name": "John"})  # Missing email
