import pytest
from pydantic import BaseModel, ValidationError
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


def test_any_of_constraint():
    """Test anyOf field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "integer"},
                        },
                        "required": ["name", "value"],
                    },
                ]
            }
        },
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Test string value
    instance = model.model_validate({"data": "test"})
    assert instance.data == "test"

    # Test number value
    instance = model.model_validate({"data": 42})
    assert instance.data == 42

    # Test object value
    instance = model.model_validate({"data": {"name": "test", "value": 123}})
    assert instance.data.name == "test"
    assert instance.data.value == 123

    # Test invalid object
    with pytest.raises(ValidationError):
        model.model_validate({"data": {"name": "test"}})  # missing required value

    # Test invalid type
    with pytest.raises(ValidationError):
        model.model_validate({"data": True})  # boolean not in anyOf


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


def test_all_of_constraint():
    """Test allOf field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        },
                        "required": ["id"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "minLength": 3},
                            "active": {"type": "boolean"}
                        },
                        "required": ["active"]
                    }
                ]
            }
        }
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Test valid data meeting all constraints
    instance = model.model_validate({
        "data": {
            "id": 1,
            "name": "test",
            "active": True
        }
    })
    assert instance.data.id == 1
    assert instance.data.name == "test"
    assert instance.data.active is True

    # Test invalid - missing required field from first schema
    with pytest.raises(ValidationError):
        model.model_validate({
            "data": {
                "name": "test",
                "active": True
            }
        })

    # Test invalid - missing required field from second schema
    with pytest.raises(ValidationError):
        model.model_validate({
            "data": {
                "id": 1,
                "name": "test"
            }
        })

    # Test invalid - name too short (constraint from second schema)
    with pytest.raises(ValidationError):
        model.model_validate({
            "data": {
                "id": 1,
                "name": "ab",
                "active": True
            }
        })

def test_local_ref_handling():
    """Test handling of local JSON Schema references."""
    schema = {
        "type": "object",
        "definitions": {
            "address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                },
                "required": ["street", "city", "country"]
            }
        },
        "properties": {
            "name": {"type": "string"},
            "home_address": {"$ref": "#/definitions/address"},
            "work_address": {"$ref": "#/definitions/address"}
        }
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Test valid data
    data = {
        "name": "John Doe",
        "home_address": {
            "street": "123 Home St",
            "city": "Hometown",
            "country": "Homeland"
        },
        "work_address": {
            "street": "456 Work Ave",
            "city": "Worktown",
            "country": "Workland"
        }
    }
    instance = model.model_validate(data)
    assert instance.name == "John Doe"
    assert instance.home_address.street == "123 Home St"
    assert instance.work_address.city == "Worktown"

    # Test invalid data - missing required field
    with pytest.raises(ValidationError):
        model.model_validate({
            "name": "John Doe",
            "home_address": {
                "street": "123 Home St"  # missing city
            }
        })

def test_circular_ref_detection():
    """Test detection of circular references."""
    schema = {
        "type": "object",
        "properties": {
            "person": {
                "$ref": "#/definitions/person"
            }
        },
        "definitions": {
            "person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "friend": {"$ref": "#/definitions/person"}
                }
            }
        }
    }

    builder = PydanticModelBuilder()
    with pytest.raises(ValueError, match="Circular reference detected"):
        builder.create_pydantic_model(schema)

def test_one_of_constraint():
    """Test oneOf field constraints validation."""
    schema = {
        "type": "object",
        "properties": {
            "pet": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "dog"},
                            "bark": {"type": "boolean"},
                        },
                        "required": ["type", "bark"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "cat"},
                            "meow": {"type": "boolean"},
                        },
                        "required": ["type", "meow"],
                    },
                ]
            }
        },
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    # Valid dog
    instance = model.model_validate({"pet": {"type": "dog", "bark": True}})
    assert instance.pet.type == "dog"
    assert instance.pet.bark is True

    # Valid cat
    instance = model.model_validate({"pet": {"type": "cat", "meow": True}})
    assert instance.pet.type == "cat"
    assert instance.pet.meow is True

    # Invalid - missing discriminator
    with pytest.raises(ValidationError):
        model.model_validate({"pet": {"bark": True}})

    # Invalid - wrong type
    with pytest.raises(ValidationError):
        model.model_validate({"pet": {"type": "fish", "swim": True}})
