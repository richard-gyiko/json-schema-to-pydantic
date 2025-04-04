import pytest
from pydantic import BaseModel, Field

# Explicitly import custom TypeError with an alias
from json_schema_to_pydantic.exceptions import TypeError as JsonSchemaTypeError
from json_schema_to_pydantic.model_builder import PydanticModelBuilder


class CustomBaseModel(BaseModel):
    test_case: str = Field(default="test", description="A test case")


def test_basic_model_creation():
    """Test basic model creation with simple properties."""
    builder = PydanticModelBuilder(base_model_type=CustomBaseModel)
    schema = {
        "title": "TestModel",
        "description": "A test model",
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }

    model = builder.create_pydantic_model(schema, CustomBaseModel)

    assert model.__name__ == "TestModel"
    assert model.__doc__ == "A test model"
    assert issubclass(model, CustomBaseModel)

    # Test instance creation
    instance = model(name="test", age=25)
    assert instance.name == "test"
    assert instance.age == 25

    # Test required field validation
    with pytest.raises(ValueError):
        model(age=25)


def test_model_builder_constructor_with_undefined_arrays():
    """Test PydanticModelBuilder constructor with allow_undefined_array_items parameter."""
    builder = PydanticModelBuilder()

    schema = {
        "type": "object",
        "properties": {
            "data": {"type": "array"}  # No items defined
        },
    }

    # Should work without explicitly passing allow_undefined_array_items to create_pydantic_model
    model = builder.create_pydantic_model(schema, allow_undefined_array_items=True)
    instance = model(data=[1, 2, 3])
    assert instance.data == [1, 2, 3]


def test_nested_model_creation():
    """Test creation of models with nested objects."""
    builder = PydanticModelBuilder()
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {"street": {"type": "string"}},
                    },
                },
            }
        },
    }

    model = builder.create_pydantic_model(schema)
    instance = model(user={"name": "John", "address": {"street": "Main St"}})

    assert isinstance(instance.user, BaseModel)
    assert isinstance(instance.user.address, BaseModel)
    assert instance.user.name == "John"
    assert instance.user.address.street == "Main St"


def test_nested_undefined_array_items():
    """Test handling of nested objects with undefined array items."""
    builder = PydanticModelBuilder()
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tags": {"type": "array"},  # No items defined
                },
            }
        },
    }

    # Should raise error with default settings
    # Use the explicit alias in pytest.raises
    with pytest.raises(JsonSchemaTypeError):
        builder.create_pydantic_model(schema)

    # Should work with allow_undefined_array_items=True
    model = builder.create_pydantic_model(schema, allow_undefined_array_items=True)
    instance = model(user={"name": "John", "tags": ["admin", "user"]})
    assert instance.user.name == "John"
    assert instance.user.tags == ["admin", "user"]


def test_model_with_references():
    """Test model creation with schema references."""
    builder = PydanticModelBuilder()
    schema = {
        "type": "object",
        "properties": {"current_pet": {"$ref": "#/definitions/Pet"}},
        "definitions": {
            "Pet": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "type": {"type": "string"}},
            }
        },
    }

    model = builder.create_pydantic_model(schema)
    instance = model(current_pet={"name": "Fluffy", "type": "cat"})

    assert isinstance(instance.current_pet, BaseModel)
    assert instance.current_pet.name == "Fluffy"


def test_model_with_combiners():
    """Test model creation with schema combiners."""
    builder = PydanticModelBuilder()
    schema = {
        "type": "object",
        "properties": {
            "mixed_field": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "a"},
                            "value": {"type": "string"},
                        },
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "b"},
                            "value": {"type": "integer"},
                        },
                    },
                ]
            }
        },
    }

    model = builder.create_pydantic_model(schema)

    # Test both variants
    instance1 = model(mixed_field={"type": "a", "value": "test"})
    instance2 = model(mixed_field={"type": "b", "value": 42})

    assert instance1.mixed_field.root.type == "a"
    assert instance1.mixed_field.root.value == "test"
    assert instance2.mixed_field.root.type == "b"
    assert instance2.mixed_field.root.value == 42


def test_complex_schema_with_undefined_arrays():
    """Test handling of complex schemas with multiple undefined arrays."""
    builder = PydanticModelBuilder()
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "tags": {"type": "array"},  # No items defined
            "metadata": {
                "type": "object",
                "properties": {
                    "categories": {"type": "array"},  # No items defined
                    "flags": {"type": "array"},  # No items defined
                },
            },
            "history": {
                "type": "array",  # Array of objects with undefined arrays
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "actions": {"type": "array"},  # No items defined
                    },
                },
            },
        },
    }

    # Should work with allow_undefined_array_items=True
    model = builder.create_pydantic_model(schema, allow_undefined_array_items=True)

    # Create a complex instance
    instance = model(
        name="Test",
        tags=["important", "urgent"],
        metadata={"categories": ["A", "B", "C"], "flags": [True, False, True]},
        history=[
            {"timestamp": "2023-01-01", "actions": ["created", "modified"]},
            {
                "timestamp": "2023-01-02",
                "actions": ["reviewed", 123, {"status": "approved"}],
            },
        ],
    )

    # Verify all data is correctly stored
    assert instance.name == "Test"
    assert instance.tags == ["important", "urgent"]
    assert instance.metadata.categories == ["A", "B", "C"]
    assert instance.metadata.flags == [True, False, True]
    # Access history items as dictionaries since they might not be converted to models
    assert instance.history[0]["timestamp"] == "2023-01-01"
    assert instance.history[0]["actions"] == ["created", "modified"]
    assert instance.history[1]["actions"] == ["reviewed", 123, {"status": "approved"}]


def test_root_level_features():
    """Test handling of root level schema features."""
    builder = PydanticModelBuilder()
    schema = {
        "title": "CustomModel",
        "description": "A model with root level features",
        "type": "object",
        "properties": {"field": {"type": "string"}},
        "$defs": {  # Test both $defs and definitions
            "SubType": {
                "type": "object",
                "properties": {"subfield": {"type": "string"}},
            }
        },
    }

    model = builder.create_pydantic_model(schema)
    assert model.__name__ == "CustomModel"
    assert model.__doc__ == "A model with root level features"

    # Test that $defs are properly handled when referenced
    schema_with_ref = {
        "type": "object",
        "properties": {"sub": {"$ref": "#/$defs/SubType"}},
    }
    model_with_ref = builder.create_pydantic_model(schema_with_ref, schema)
    instance = model_with_ref(sub={"subfield": "test"})
    assert instance.sub.subfield == "test"


def test_undefined_array_items():
    """Test handling of arrays without defined item types."""
    # Test with default behavior (should raise error)
    builder = PydanticModelBuilder()
    schema = {"type": "object", "properties": {"tags": {"type": "array"}}}

    # Use the explicit alias in pytest.raises
    with pytest.raises(
        JsonSchemaTypeError, match="Array type must specify 'items' schema"
    ):
        builder.create_pydantic_model(schema)

    # Test with allow_undefined_array_items=True
    model = builder.create_pydantic_model(schema, allow_undefined_array_items=True)

    # Should create a model with List[Any] field
    instance = model(tags=["tag1", "tag2"])
    assert instance.tags == ["tag1", "tag2"]

    # Should accept any type of items
    instance = model(tags=[1, "two", 3.0, True])
    assert instance.tags == [1, "two", 3.0, True]


def test_create_model_function():
    """Test the create_model function from the package."""
    from json_schema_to_pydantic import create_model

    # Test with undefined array items and allow_undefined_array_items=True
    schema = {"type": "object", "properties": {"tools": {"type": "array"}}}

    # Should raise error with default settings
    # Use the explicit alias in pytest.raises
    with pytest.raises(JsonSchemaTypeError):
        model = create_model(schema)

    # Should work with allow_undefined_array_items=True
    model = create_model(schema, allow_undefined_array_items=True)
    instance = model(tools=["hammer", "screwdriver"])
    assert instance.tools == ["hammer", "screwdriver"]
