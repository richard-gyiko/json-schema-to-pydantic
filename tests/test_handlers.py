import pytest
from json_schema_to_pydantic.handlers import CombinerHandler
from json_schema_to_pydantic.exceptions import CombinerError
from pydantic import BaseModel


def test_all_of_handler():
    handler = CombinerHandler()

    schemas = [
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        },
    ]

    model = handler.handle_all_of(schemas, {})
    assert issubclass(model, BaseModel)

    # Validate merged model
    instance = model(name="John", age=30)
    assert instance.name == "John"
    assert instance.age == 30


def test_any_of_handler():
    handler = CombinerHandler()

    schemas = [{"type": "string"}, {"type": "integer"}]

    union_type = handler.handle_any_of(schemas, {})
    from typing import Union

    assert Union[str, int] == union_type


def test_one_of_handler():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {"type": {"const": "dog"}, "bark": {"type": "boolean"}},
            },
            {
                "type": "object",
                "properties": {"type": {"const": "cat"}, "meow": {"type": "boolean"}},
            },
        ]
    }

    model = handler.handle_one_of(schema, {})
    assert issubclass(model, BaseModel)


def test_all_of_with_conflicting_constraints():
    handler = CombinerHandler()

    schemas = [
        {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 100}},
        },
        {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 50, "maximum": 75}},
        },
    ]

    model = handler.handle_all_of(schemas, {})
    instance = model(value=60)
    assert instance.value == 60

    with pytest.raises(ValueError):
        model(value=25)  # Below merged minimum

    with pytest.raises(ValueError):
        model(value=80)  # Above merged maximum


def test_any_of_with_mixed_types():
    handler = CombinerHandler()

    schemas = [
        {"type": "string", "minLength": 3},
        {"type": "integer", "minimum": 0},
        {"type": "object", "properties": {"name": {"type": "string"}}},
    ]

    union_type = handler.handle_any_of(schemas, {})
    # Verify the union includes all types
    assert str in union_type.__args__
    assert int in union_type.__args__
    assert any(issubclass(t, BaseModel) for t in union_type.__args__)


def test_one_of_validation():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "circle"},
                    "radius": {"type": "number"},
                },
                "required": ["type", "radius"],
            },
            {
                "type": "object",
                "properties": {
                    "type": {"const": "rectangle"},
                    "width": {"type": "number"},
                    "height": {"type": "number"},
                },
                "required": ["type", "width", "height"],
            },
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Test circle
    circle = model(type="circle", radius=5.0)
    assert circle.root.type == "circle"
    assert circle.root.radius == 5.0

    # Test rectangle
    rectangle = model(type="rectangle", width=10.0, height=20.0)
    assert rectangle.root.type == "rectangle"
    assert rectangle.root.width == 10.0
    assert rectangle.root.height == 20.0

    # Test invalid type
    with pytest.raises(ValueError):
        model(type="triangle", sides=3)


def test_empty_combiners():
    handler = CombinerHandler()

    with pytest.raises(CombinerError):
        handler.handle_all_of([], {})

    with pytest.raises(CombinerError):
        handler.handle_any_of([], {})

    with pytest.raises(CombinerError):
        handler.handle_one_of({"oneOf": []}, {})


def test_one_of_invalid_schema():
    handler = CombinerHandler()

    # Test with non-dict schema
    invalid_schema = {"oneOf": ["not a valid schema", {"type": "object"}]}
    with pytest.raises(CombinerError):
        handler.handle_one_of(invalid_schema, {})


def test_one_of_missing_discriminator():
    handler = CombinerHandler()

    # Schema missing type const
    invalid_schema = {
        "oneOf": [{"type": "object", "properties": {"name": {"type": "string"}}}]
    }
    with pytest.raises(CombinerError):
        handler.handle_one_of(invalid_schema, {})


def test_one_of_nested():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "parent"},
                    "child": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "type": {"const": "child1"},
                                    "value": {"type": "string"},
                                },
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "type": {"const": "child2"},
                                    "value": {"type": "integer"},
                                },
                            },
                        ]
                    },
                },
            }
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Test nested discriminated union
    instance = model(type="parent", child={"type": "child1", "value": "test"})
    assert instance.root.type == "parent"
    assert instance.root.child.root.type == "child1"
    assert instance.root.child.root.value == "test"
    assert instance.root.child.root.type == "child1"
    assert instance.root.child.root.value == "test"


def test_one_of_required_fields():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "user"},
                    "username": {"type": "string"},
                },
                "required": ["type", "username"],
            }
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Test missing required field
    with pytest.raises(ValueError):
        model(root={"type": "user"})  # Missing required username


def test_optional_fields():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "user"},
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "description": {"type": "string"},
                },
                "required": ["type", "username"],  # email and description are optional
            }
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Test with only required fields
    instance = model(root={"type": "user", "username": "test"})
    assert instance.root.type == "user"
    assert instance.root.username == "test"
    assert instance.root.email is None
    assert instance.root.description is None


def test_field_descriptions():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "user", "description": "The type of user"},
                    "username": {
                        "type": "string",
                        "description": "The user's username",
                    },
                },
                "required": ["type", "username"],
            }
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Get field info from model
    field_info = model.model_fields["root"].annotation.model_fields
    assert field_info["type"].description == "The type of user"
    assert field_info["username"].description == "The user's username"


def test_one_of_invalid_discriminator():
    handler = CombinerHandler()

    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "option1"},
                    "value": {"type": "string"},
                },
            }
        ]
    }

    model = handler.handle_one_of(schema, {})

    # Test invalid discriminator value
    with pytest.raises(ValueError):
        model(type="invalid_option", value="test")
