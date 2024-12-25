import pytest
from pydantic import BaseModel
from autogen_mcp_tool_adapter.pydantic_model_builder import PydanticModelBuilder


def test_basic_types():
    """Test basic type validation and conversion."""
    schema = {
        "type": "object",
        "properties": {
            "string_field": {"type": "string"},
            "integer_field": {"type": "integer"},
            "number_field": {"type": "number"},
            "boolean_field": {"type": "boolean"},
            "array_field": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["string_field", "array_field"],
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Test valid data
    valid_data = {
        "string_field": "test",
        "array_field": ["item1", "item2"],
        "integer_field": 42,
        "number_field": 3.14,
        "boolean_field": True,
    }
    instance = model.model_validate(valid_data)

    assert isinstance(instance, BaseModel)
    assert instance.string_field == "test"
    assert instance.array_field == ["item1", "item2"]
    assert instance.integer_field == 42
    assert instance.number_field == 3.14
    assert instance.boolean_field is True

    # Test missing required field
    with pytest.raises(ValueError):
        model.model_validate({"integer_field": 42})


def test_string_constraints():
    """Test string field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20,
                "pattern": "^[a-zA-Z0-9_]+$",
            }
        },
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Valid username
    instance = model.model_validate({"username": "valid_user123"})
    assert instance.username == "valid_user123"

    # Too short
    with pytest.raises(ValueError):
        model.model_validate({"username": "ab"})

    # Too long
    with pytest.raises(ValueError):
        model.model_validate({"username": "a" * 21})

    # Invalid pattern
    with pytest.raises(ValueError):
        model.model_validate({"username": "invalid@user"})


def test_number_constraints():
    """Test numeric field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer", "minimum": 0, "maximum": 120},
            "score": {
                "type": "number",
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 100,
                "multipleOf": 0.5,
            },
        },
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Valid values
    instance = model.model_validate({"age": 25, "score": 95.5})
    assert instance.age == 25
    assert instance.score == 95.5

    # Invalid age
    with pytest.raises(ValueError):
        model.model_validate({"age": -1, "score": 50})

    # Invalid score
    with pytest.raises(ValueError):
        model.model_validate({"age": 25, "score": 100})  # exclusive maximum

    # Invalid multiple
    with pytest.raises(ValueError):
        model.model_validate({"age": 25, "score": 95.7})  # not multiple of 0.5


def test_array_constraints():
    """Test array field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
            }
        },
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Valid array
    instance = model.model_validate({"tags": ["python", "coding"]})
    assert set(instance.tags) == {"python", "coding"}

    # Empty array
    with pytest.raises(ValueError):
        model.model_validate({"tags": []})

    # Too many items
    with pytest.raises(ValueError):
        model.model_validate({"tags": ["a", "b", "c", "d"]})

    # Duplicate items should be automatically handled by Set type
    instance = model.model_validate({"tags": ["python", "python"]})
    assert set(instance.tags) == {"python"}
