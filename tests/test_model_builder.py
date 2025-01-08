import pytest
from pydantic import BaseModel, Field
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
