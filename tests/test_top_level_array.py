"""Tests for top-level array schemas."""
import pytest
from pydantic import BaseModel, RootModel, ValidationError

from json_schema_to_pydantic import create_model
from json_schema_to_pydantic.exceptions import TypeError as JsonSchemaTypeError


def test_basic_top_level_array():
    """Test basic top-level array with object items."""
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
        },
    }
    data = [{"value": "42"}, {"value": "3.14"}]

    Model = create_model(schema)
    
    # Verify it's a RootModel
    assert issubclass(Model, RootModel)
    
    # Validate and check the data
    model = Model.model_validate(data)
    assert len(model.root) == 2
    assert model.root[0].value == 42.0
    assert model.root[1].value == 3.14
    
    # Check JSON serialization
    json_output = model.model_dump_json()
    assert json_output == '[{"value":42.0},{"value":3.14}]'


def test_top_level_array_with_simple_items():
    """Test top-level array with simple string items."""
    schema = {
        "type": "array",
        "items": {"type": "string"}
    }
    data = ["apple", "banana", "cherry"]

    Model = create_model(schema)
    model = Model.model_validate(data)
    
    assert model.root == ["apple", "banana", "cherry"]
    assert model.model_dump_json() == '["apple","banana","cherry"]'


def test_top_level_array_with_number_items():
    """Test top-level array with number items."""
    schema = {
        "type": "array",
        "items": {"type": "number"}
    }
    data = [1, 2.5, 3.14]

    Model = create_model(schema)
    model = Model.model_validate(data)
    
    assert model.root == [1, 2.5, 3.14]


def test_top_level_array_minItems_constraint():
    """Test top-level array with minItems constraint."""
    schema = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 2
    }

    Model = create_model(schema)
    
    # Should succeed with 2 or more items
    model = Model.model_validate(["a", "b"])
    assert len(model.root) == 2
    
    model = Model.model_validate(["a", "b", "c"])
    assert len(model.root) == 3
    
    # Should fail with less than 2 items
    with pytest.raises(ValidationError):
        Model.model_validate(["a"])


def test_top_level_array_maxItems_constraint():
    """Test top-level array with maxItems constraint."""
    schema = {
        "type": "array",
        "items": {"type": "string"},
        "maxItems": 3
    }

    Model = create_model(schema)
    
    # Should succeed with 3 or fewer items
    model = Model.model_validate(["a", "b", "c"])
    assert len(model.root) == 3
    
    # Should fail with more than 3 items
    with pytest.raises(ValidationError):
        Model.model_validate(["a", "b", "c", "d"])


def test_top_level_array_minItems_and_maxItems():
    """Test top-level array with both minItems and maxItems constraints."""
    schema = {
        "type": "array",
        "items": {"type": "integer"},
        "minItems": 2,
        "maxItems": 5
    }

    Model = create_model(schema)
    
    # Should succeed with 2-5 items
    for count in range(2, 6):
        data = list(range(count))
        model = Model.model_validate(data)
        assert len(model.root) == count
    
    # Should fail with 1 item
    with pytest.raises(ValidationError):
        Model.model_validate([1])
    
    # Should fail with 6 items
    with pytest.raises(ValidationError):
        Model.model_validate([1, 2, 3, 4, 5, 6])


def test_top_level_array_uniqueItems():
    """Test top-level array with uniqueItems constraint."""
    schema = {
        "type": "array",
        "items": {"type": "string"},
        "uniqueItems": True
    }

    Model = create_model(schema)
    model = Model.model_validate(["a", "b", "c"])
    
    # Should be a set
    assert isinstance(model.root, set)
    assert model.root == {"a", "b", "c"}
    
    # Duplicates should be automatically removed by set
    model = Model.model_validate(["a", "b", "a", "c"])
    assert len(model.root) == 3
    assert model.root == {"a", "b", "c"}


def test_top_level_array_with_title():
    """Test that title is properly used for top-level array models."""
    schema = {
        "title": "MyArrayModel",
        "type": "array",
        "items": {"type": "string"}
    }

    Model = create_model(schema)
    assert Model.__name__ == "MyArrayModel"


def test_top_level_array_with_description():
    """Test that description is properly used for top-level array models."""
    schema = {
        "type": "array",
        "description": "A list of items",
        "items": {"type": "string"}
    }

    Model = create_model(schema)
    assert Model.__doc__ == "A list of items"


def test_top_level_array_nested_objects():
    """Test top-level array with complex nested objects."""
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"}
                    }
                }
            },
            "required": ["name"]
        }
    }
    
    data = [
        {
            "name": "John",
            "age": 30,
            "address": {"street": "Main St", "city": "NYC"}
        },
        {
            "name": "Jane",
            "age": 25
        }
    ]

    Model = create_model(schema)
    model = Model.model_validate(data)
    
    assert len(model.root) == 2
    assert model.root[0].name == "John"
    assert model.root[0].age == 30
    assert model.root[0].address.street == "Main St"
    assert model.root[1].name == "Jane"
    assert model.root[1].age == 25


def test_top_level_array_without_items_raises_error():
    """Test that array without items schema raises an error."""
    schema = {
        "type": "array"
        # No items defined
    }

    with pytest.raises(JsonSchemaTypeError, match="Array type must specify 'items' schema"):
        create_model(schema)


def test_top_level_array_without_items_with_flag():
    """Test array without items schema works with allow_undefined_array_items flag."""
    schema = {
        "type": "array"
        # No items defined
    }

    Model = create_model(schema, allow_undefined_array_items=True)
    
    # Should accept any items
    model = Model.model_validate([1, "two", 3.0, True, None])
    assert len(model.root) == 5


def test_top_level_array_validation_errors():
    """Test that validation errors work correctly for top-level arrays."""
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "required": ["value"]
        }
    }

    Model = create_model(schema)
    
    # Should fail if required field is missing
    with pytest.raises(ValidationError) as exc_info:
        Model.model_validate([{"value": 42}, {}])
    
    assert "value" in str(exc_info.value).lower()


def test_top_level_array_with_ref_items():
    """Test top-level array with items defined via $ref."""
    schema = {
        "type": "array",
        "items": {"$ref": "#/$defs/Item"},
        "$defs": {
            "Item": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                },
                "required": ["id"]
            }
        }
    }
    
    data = [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"}
    ]

    Model = create_model(schema)
    model = Model.model_validate(data)
    
    assert len(model.root) == 2
    assert model.root[0].id == 1
    assert model.root[0].name == "Item 1"
    assert model.root[1].id == 2


def test_array_as_property_still_works():
    """Test that arrays as object properties still work (regression test)."""
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"value": {"type": "number"}},
                    "required": ["value"]
                }
            }
        }
    }
    
    data = {"items": [{"value": "42"}, {"value": "3.14"}]}

    Model = create_model(schema)
    
    # Should NOT be a RootModel
    assert not issubclass(Model, RootModel)
    assert issubclass(Model, BaseModel)
    
    model = Model.model_validate(data)
    assert len(model.items) == 2
    assert model.items[0].value == 42.0
    assert model.items[1].value == 3.14


def test_top_level_array_empty():
    """Test that empty arrays are handled correctly."""
    schema = {
        "type": "array",
        "items": {"type": "string"}
    }

    Model = create_model(schema)
    model = Model.model_validate([])
    
    assert model.root == []
    assert model.model_dump_json() == "[]"


def test_top_level_array_with_custom_base_model():
    """Test top-level array with custom base model type."""
    class CustomBase(BaseModel):
        custom_field: str = "custom"
    
    schema = {
        "type": "array",
        "items": {"type": "string"}
    }
    
    # Note: RootModel doesn't inherit from custom base in the same way,
    # but we should still be able to create the model
    Model = create_model(schema, base_model_type=CustomBase)
    
    model = Model.model_validate(["a", "b", "c"])
    assert model.root == ["a", "b", "c"]


def test_top_level_array_extra_properties():
    """Test that non-standard properties are properly handled in json_schema_extra."""
    schema = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "customField": "customValue",
        "anotherCustom": 123
    }
    
    Model = create_model(schema)
    
    # Standard array properties (items, minItems) should not be in json_schema_extra
    # Only custom properties should be there
    if hasattr(Model, 'model_config') and Model.model_config:
        config_dict = Model.model_config
        if 'json_schema_extra' in config_dict:
            extra = config_dict['json_schema_extra']
            # Custom properties should be present
            assert "customField" in extra
            assert extra["customField"] == "customValue"
            assert "anotherCustom" in extra
            assert extra["anotherCustom"] == 123
            # Standard properties should not be in extra
            assert "items" not in extra
            assert "minItems" not in extra
            assert "type" not in extra
    
    # Model should still work correctly
    model = Model.model_validate(["a", "b"])
    assert model.root == ["a", "b"]
