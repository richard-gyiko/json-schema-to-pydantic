from typing import Union

import pytest
from pydantic import BaseModel, Field, RootModel, create_model

from json_schema_to_pydantic.builders import ConstraintBuilder
from json_schema_to_pydantic.exceptions import CombinerError
from json_schema_to_pydantic.handlers import CombinerHandler
from json_schema_to_pydantic.resolvers import ReferenceResolver, TypeResolver


# Helper function to create handler with dependencies
def create_handler():
    # Instantiate necessary components
    type_resolver = TypeResolver()
    constraint_builder = ConstraintBuilder()
    reference_resolver = ReferenceResolver()

    # Define simple callbacks for testing purposes
    # Note: These might need adjustment if tests require full model building recursion
    def simple_recursive_builder(
        schema, root_schema, allow_undefined_array_items=False
    ):
        # Resolve $ref first, similar to PydanticModelBuilder._get_field_type
        if "$ref" in schema:
            schema = reference_resolver.resolve_ref(schema["$ref"], schema, root_schema)

        # Basic type resolution for testing handlers
        if schema.get("type") == "object":
            # Simulate basic object model creation for tests needing nested structures
            props = schema.get("properties", {})
            req = schema.get("required", [])
            fields = {
                n: (
                    simple_recursive_builder(
                        p, root_schema, allow_undefined_array_items
                    ),
                    simple_field_info_builder(p, n in req),
                )
                for n, p in props.items()
            }
            return create_model("NestedTestModel", **fields)
        elif "oneOf" in schema:
            # Delegate back to a temporary handler instance for nested oneOf
            # This is a bit complex for a simple test setup, might need refinement
            temp_handler = CombinerHandler(
                type_resolver,
                constraint_builder,
                reference_resolver,
                simple_recursive_builder,
                simple_field_info_builder,
            )
            return temp_handler.handle_one_of(
                schema, root_schema, allow_undefined_array_items
            )
        elif "anyOf" in schema:
            temp_handler = CombinerHandler(
                type_resolver,
                constraint_builder,
                reference_resolver,
                simple_recursive_builder,
                simple_field_info_builder,
            )
            return temp_handler.handle_any_of(
                schema["anyOf"], root_schema, allow_undefined_array_items
            )
        # Fallback to basic type resolver
        return type_resolver.resolve_type(
            schema, root_schema, allow_undefined_array_items
        )

    def simple_field_info_builder(schema, required):
        # Basic field info creation for testing
        kwargs = {}
        constraints = constraint_builder.build_constraints(schema)
        if isinstance(constraints, dict):
            kwargs.update(constraints)
        if "default" in schema:
            kwargs["default"] = schema["default"]
        elif not required:
            kwargs["default"] = None
        if "description" in schema:
            kwargs["description"] = schema["description"]
        return Field(**kwargs)

    # Return the handler instance with dependencies and callbacks
    return CombinerHandler(
        type_resolver=type_resolver,
        constraint_builder=constraint_builder,
        reference_resolver=reference_resolver,
        recursive_field_builder=simple_recursive_builder,
        field_info_builder=simple_field_info_builder,
    )


def test_all_of_handler():
    handler = create_handler()

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
    handler = create_handler()

    schemas = [{"type": "string"}, {"type": "integer"}]

    union_type = handler.handle_any_of(schemas, {})

    assert Union[str, int] == union_type


def test_one_of_handler():
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

    with pytest.raises(CombinerError):
        handler.handle_all_of([], {})

    with pytest.raises(CombinerError):
        handler.handle_any_of([], {})

    with pytest.raises(CombinerError):
        handler.handle_one_of({"oneOf": []}, {})


def test_one_of_invalid_schema():
    handler = create_handler()

    # Test with non-dict schema
    invalid_schema = {"oneOf": ["not a valid schema", {"type": "object"}]}
    with pytest.raises(CombinerError):
        handler.handle_one_of(invalid_schema, {})


def test_one_of_missing_discriminator():
    handler = create_handler()

    # Schema missing type const
    invalid_schema = {
        "oneOf": [{"type": "object", "properties": {"name": {"type": "string"}}}]
    }
    with pytest.raises(CombinerError):
        handler.handle_one_of(invalid_schema, {})


def test_one_of_nested():
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

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
    handler = create_handler()

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


def test_any_of_with_ref():
    """Test anyOf handler with a $ref."""
    handler = create_handler()

    root_schema = {
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"street": {"type": "string"}},
                "required": ["street"],
            }
        }
    }
    schemas = [{"type": "string"}, {"$ref": "#/$defs/Address"}]

    union_type = handler.handle_any_of(schemas, root_schema)

    # Check that the Union includes str and a BaseModel derived from Address
    assert str in union_type.__args__
    assert any(
        issubclass(t, BaseModel) and "street" in t.model_fields
        for t in union_type.__args__
    )


def test_one_of_with_ref():
    """Test oneOf handler with a $ref."""
    handler = create_handler()

    root_schema = {
        "$defs": {
            "Cat": {
                "type": "object",
                "properties": {
                    "type": {"const": "cat", "description": "Type discriminator"},
                    "meow_volume": {"type": "integer"},
                },
                "required": ["type", "meow_volume"],
            }
        }
    }
    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "dog"},
                    "bark_pitch": {"type": "string"},
                },
                "required": ["type", "bark_pitch"],
            },
            {"$ref": "#/$defs/Cat"},
        ]
    }

    model = handler.handle_one_of(schema, root_schema)
    assert issubclass(model, RootModel)

    # Test dog variant
    dog_instance = model(root={"type": "dog", "bark_pitch": "high"})
    assert dog_instance.root.type == "dog"
    assert dog_instance.root.bark_pitch == "high"

    # Test cat variant (resolved from $ref)
    cat_instance = model(root={"type": "cat", "meow_volume": 10})
    assert cat_instance.root.type == "cat"
    assert cat_instance.root.meow_volume == 10

    # Check field descriptions from referenced schema
    # Access the Union arguments inside Annotated: annotation.__args__[0].__args__
    union_args = model.model_fields["root"].annotation.__args__[0].__args__
    cat_model = next(t for t in union_args if t.__name__ == "Cat")
    assert cat_model.model_fields["type"].description == "Type discriminator"


def test_any_of_property_with_ref():
    """Test a property using anyOf containing a $ref."""
    handler = create_handler()
    root_schema = {
        "$defs": {
            "SimpleObject": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            }
        },
        "type": "object",
        "properties": {
            "data": {
                "anyOf": [
                    {"type": "string"},
                    {"$ref": "#/$defs/SimpleObject"},
                ]
            }
        },
    }

    # We need to simulate how ModelBuilder calls the handler for a property
    prop_schema = root_schema["properties"]["data"]
    union_type = handler.handle_any_of(prop_schema["anyOf"], root_schema)

    assert str in union_type.__args__
    assert any(
        issubclass(t, BaseModel) and "id" in t.model_fields for t in union_type.__args__
    )


def test_one_of_property_with_ref():
    """Test a property using oneOf containing a $ref."""
    handler = create_handler()
    root_schema = {
        "$defs": {
            "RefOption": {
                "type": "object",
                "properties": {
                    "type": {"const": "ref_opt"},
                    "value": {"type": "boolean"},
                },
                "required": ["type", "value"],
            }
        },
        "type": "object",
        "properties": {
            "choice": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "inline_opt"},
                            "value": {"type": "string"},
                        },
                        "required": ["type", "value"],
                    },
                    {"$ref": "#/$defs/RefOption"},
                ]
            }
        },
    }

    # Simulate ModelBuilder call for the property
    prop_schema = root_schema["properties"]["choice"]
    model = handler.handle_one_of(prop_schema, root_schema)

    assert issubclass(model, RootModel)

    # Test inline variant
    inline_instance = model(root={"type": "inline_opt", "value": "hello"})
    assert inline_instance.root.type == "inline_opt"
    assert inline_instance.root.value == "hello"

    # Test referenced variant
    ref_instance = model(root={"type": "ref_opt", "value": True})
    assert ref_instance.root.type == "ref_opt"
    assert ref_instance.root.value is True


def test_all_of_with_top_level_ref():
    """Test allOf handler with a top-level $ref in the list."""
    handler = create_handler()
    root_schema = {
        "$defs": {
            "NameSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        }
    }
    schemas = [
        {"$ref": "#/$defs/NameSchema"},
        {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        },
    ]

    model = handler.handle_all_of(schemas, root_schema)
    assert issubclass(model, BaseModel)

    # Validate merged model includes fields from the referenced schema
    instance = model(name="Alice", age=30)
    assert instance.name == "Alice"
    assert instance.age == 30

    # Check required fields from both schemas
    with pytest.raises(ValueError):
        model(name="Alice")  # Missing age
    with pytest.raises(ValueError):
        model(age=30)  # Missing name


def test_all_of_with_property_ref():
    """Test allOf handler where a property uses $ref."""
    handler = create_handler()
    root_schema = {
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                },
                "required": ["street", "city"],
            }
        }
    }
    schemas = [
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        {
            "type": "object",
            "properties": {"location": {"$ref": "#/$defs/Address"}},
            "required": ["location"],
        },
    ]

    model = handler.handle_all_of(schemas, root_schema)
    assert issubclass(model, BaseModel)

    # Validate merged model includes the referenced property type
    instance = model(name="Bob", location={"street": "123 Main St", "city": "Anytown"})
    assert instance.name == "Bob"
    assert isinstance(instance.location, BaseModel)
    assert instance.location.street == "123 Main St"
    assert instance.location.city == "Anytown"

    # Check required fields
    with pytest.raises(ValueError):
        model(name="Bob")  # Missing location
    with pytest.raises(ValueError):
        model(location={"street": "123 Main St", "city": "Anytown"})  # Missing name
    with pytest.raises(ValueError):
        # Missing required field within the referenced Address model
        model(name="Bob", location={"street": "123 Main St"})


def test_all_of_merging_ref_and_inline():
    """Test merging a schema defined by $ref with an inline schema."""
    handler = create_handler()
    root_schema = {
        "$defs": {
            "BaseInfo": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "description": {"type": "string"},
                },
                "required": ["id"],
            }
        }
    }
    schemas = [
        {"$ref": "#/$defs/BaseInfo"},
        {
            "type": "object",
            "properties": {
                "description": {"minLength": 10},  # Add constraint to existing field
                "status": {"type": "string", "enum": ["active", "inactive"]},
            },
            "required": ["status"],  # Add new required field
        },
    ]

    model = handler.handle_all_of(schemas, root_schema)
    assert issubclass(model, BaseModel)

    # Validate merged model
    instance = model(id=1, description="A long description", status="active")
    assert instance.id == 1
    assert instance.description == "A long description"
    assert instance.status == "active"

    # Check merged constraints and required fields
    with pytest.raises(ValueError):
        model(id=1, description="short", status="active")  # Fails minLength
    with pytest.raises(ValueError):
        model(id=1, description="A long description")  # Missing status
    with pytest.raises(ValueError):
        model(description="A long description", status="active")  # Missing id
