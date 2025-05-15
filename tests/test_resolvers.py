import pytest

# Explicitly import custom TypeError with an alias
from json_schema_to_pydantic.exceptions import (
    ReferenceError,
)
from json_schema_to_pydantic.exceptions import (
    TypeError as JsonSchemaTypeError,
)
from json_schema_to_pydantic.resolvers import ReferenceResolver, TypeResolver


def test_type_resolver_basic_types():
    resolver = TypeResolver()

    assert resolver.resolve_type({"type": "string"}, {}) is str
    assert resolver.resolve_type({"type": "integer"}, {}) is int
    assert resolver.resolve_type({"type": "number"}, {}) is float
    assert resolver.resolve_type({"type": "boolean"}, {}) is bool


def test_type_resolver_array():
    resolver = TypeResolver()

    schema = {"type": "array", "items": {"type": "string"}}
    from typing import List

    assert resolver.resolve_type(schema, {}) == List[str]


def test_type_resolver_undefined_array_items():
    """Test handling of arrays without defined item types."""
    resolver = TypeResolver()
    from typing import Any, List

    # Test with undefined items and allow_undefined_array_items=False (default)
    schema = {"type": "array"}
    # Use the explicit alias in pytest.raises
    with pytest.raises(
        JsonSchemaTypeError, match="Array type must specify 'items' schema"
    ):
        resolver.resolve_type(schema, {})

    # Test with undefined items and allow_undefined_array_items=True
    result = resolver.resolve_type(schema, {}, allow_undefined_array_items=True)
    assert result == List[Any]


def test_reference_resolver():
    resolver = ReferenceResolver()

    root_schema = {
        "definitions": {
            "pet": {"type": "object", "properties": {"name": {"type": "string"}}}
        }
    }

    result = resolver.resolve_ref("#/definitions/pet", {}, root_schema)
    assert result["type"] == "object"
    assert "name" in result["properties"]


def test_invalid_reference_path():
    """Test handling of invalid reference paths."""
    resolver = ReferenceResolver()
    schema = {"$ref": "#/invalid/path"}
    root_schema = {"valid": {"field": "value"}}

    with pytest.raises(ReferenceError, match="Invalid reference path"):
        resolver.resolve_ref("#/invalid/path", schema, root_schema)


def test_external_reference_rejection():
    """Test rejection of external references."""
    resolver = ReferenceResolver()
    schema = {"$ref": "http://example.com/schema"}
    root_schema = {}

    with pytest.raises(ReferenceError, match="Only local references"):
        resolver.resolve_ref("http://example.com/schema", schema, root_schema)


def test_nested_reference_resolution():
    """Test resolution of nested references."""
    resolver = ReferenceResolver()
    root_schema = {
        "definitions": {
            "address": {"type": "object", "properties": {"street": {"type": "string"}}},
            "person": {"$ref": "#/definitions/address"},
        }
    }

    result = resolver.resolve_ref("#/definitions/person", {}, root_schema)
    assert result == {"type": "object", "properties": {"street": {"type": "string"}}}


def test_circular_reference_detection():
    """Test detection of circular references."""
    resolver = ReferenceResolver()
    root_schema = {
        "definitions": {
            "person": {
                "type": "object",
                "properties": {"friend": {"$ref": "#/definitions/person"}},
            }
        }
    }

    with pytest.raises(ReferenceError, match="Circular reference detected"):
        resolver.resolve_ref("#/definitions/person", {}, root_schema)


def test_json_pointer_escaping():
    """Test handling of escaped JSON Pointer characters."""
    resolver = ReferenceResolver()
    root_schema = {"definitions": {"special/~name": {"type": "string"}}}

    result = resolver.resolve_ref("#/definitions/special~1~0name", {}, root_schema)
    assert result == {"type": "string"}


def test_type_resolver_complex_types():
    """Test resolution of complex types like arrays and objects."""
    resolver = TypeResolver()

    # Test nested array
    nested_array_schema = {
        "type": "array",
        "items": {"type": "array", "items": {"type": "string"}},
    }
    from typing import List

    assert resolver.resolve_type(nested_array_schema, {}) == List[List[str]]

    # Test object with nested types
    object_schema = {
        "type": "object",
        "properties": {
            "strings": {"type": "array", "items": {"type": "string"}},
            "numbers": {"type": "array", "items": {"type": "number"}},
        },
    }
    result_type = resolver.resolve_type(object_schema, {})
    assert issubclass(result_type, dict)


def test_type_resolver_format_handling():
    """Test handling of format specifications."""
    resolver = TypeResolver()
    from datetime import datetime
    from uuid import UUID

    from pydantic import AnyUrl

    assert (
        resolver.resolve_type({"type": "string", "format": "date-time"}, {}) == datetime
    )
    assert resolver.resolve_type({"type": "string", "format": "email"}, {}) is str
    assert resolver.resolve_type({"type": "string", "format": "uri"}, {}) == AnyUrl
    assert resolver.resolve_type({"type": "string", "format": "uuid"}, {}) == UUID


def test_type_resolver_enum():
    """Test handling of enum types."""
    resolver = TypeResolver()
    from typing import Literal

    schema = {"type": "string", "enum": ["red", "green", "blue"]}
    result = resolver.resolve_type(schema, {})
    assert result == Literal["red", "green", "blue"]


def test_type_resolver_const():
    """Test handling of const values."""
    resolver = TypeResolver()
    from typing import Any, Literal, Optional

    schema = {"const": 42}
    result = resolver.resolve_type(schema, {})
    assert result == Literal[42]

    # Test null const
    schema = {"const": None}
    result = resolver.resolve_type(schema, {})
    assert result == Optional[Any]


def test_type_resolver_null():
    """Test handling of null type."""
    resolver = TypeResolver()
    from typing import Any, Optional

    schema = {"type": "null"}
    result = resolver.resolve_type(schema, {})
    assert result == Optional[Any]

    # Test nullable string
    schema = {"type": ["string", "null"]}
    result = resolver.resolve_type(schema, {})
    assert result == Optional[str]


def test_reference_resolver_nested_definitions():
    """Test resolution of nested definitions."""
    resolver = ReferenceResolver()

    root_schema = {
        "definitions": {
            "size": {
                "type": "object",
                "properties": {
                    "width": {"type": "number"},
                    "height": {"type": "number"},
                },
            },
            "shape": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "size": {"$ref": "#/definitions/size"},
                },
            },
        }
    }

    result = resolver.resolve_ref("#/definitions/shape", {}, root_schema)
    assert result["type"] == "object"
    assert "name" in result["properties"]
    assert result["properties"]["size"] == root_schema["definitions"]["size"]


def test_reference_resolver_array_refs():
    """Test resolution of references in array items."""
    resolver = ReferenceResolver()

    root_schema = {
        "definitions": {
            "point": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
            }
        }
    }

    schema = {"type": "array", "items": {"$ref": "#/definitions/point"}}

    result = resolver.resolve_ref("#/definitions/point", schema, root_schema)
    assert result["type"] == "object"
    assert "x" in result["properties"]
    assert "y" in result["properties"]


def test_reference_resolver_invalid_path_segments():
    """Test handling of invalid path segments in references."""
    resolver = ReferenceResolver()

    root_schema = {"definitions": {"valid": {"type": "string"}}}

    with pytest.raises(ReferenceError, match="Invalid reference path"):
        resolver.resolve_ref("#/invalid/path/segments", {}, root_schema)


def test_reference_resolver_empty_path():
    """Test handling of empty reference paths."""
    resolver = ReferenceResolver()

    with pytest.raises(ReferenceError):
        resolver.resolve_ref("", {}, {})


def test_reference_resolver_malformed_ref():
    """Test handling of malformed references."""
    resolver = ReferenceResolver()

    with pytest.raises(ReferenceError):
        resolver.resolve_ref("not/a/valid/ref", {}, {})


def test_type_resolver_nested_array_references():
    """Test handling of nested references in array items."""
    resolver = TypeResolver()

    # Create a schema with a reference in an array item
    root_schema = {
        "definitions": {
            "data": {
                "type": "object",
                "properties": {"b": {"type": "integer"}},
                "required": ["b"],
            }
        },
        "type": "object",
        "properties": {"a": {"type": "array", "items": {"$ref": "#/definitions/data"}}},
        "required": ["a"],
    }

    # Test resolving the array type with nested reference
    array_schema = root_schema["properties"]["a"]
    result_type = resolver.resolve_type(array_schema, root_schema)

    from typing import get_args, get_origin

    # The result should be List[dict]
    assert get_origin(result_type) is list
    assert get_args(result_type)[0] is dict

    # Verify we can create and validate a model with this schema
    from json_schema_to_pydantic import create_model

    model = create_model(root_schema)
    instance = model.model_validate({"a": [{"b": 1}, {"b": 2}]})
    # Access as dictionary items since they're dictionaries, not models
    assert instance.a[0]["b"] == 1
    assert instance.a[1]["b"] == 2


def test_type_resolver_complex_nested_references():
    """Test handling of complex nested references in array items."""
    resolver = TypeResolver()

    # Create a more complex schema with nested references
    root_schema = {
        "definitions": {
            "nested_item": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "integer"},
                },
                "required": ["name", "value"],
            },
            "complex_item": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "nested_items": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/nested_item"},
                    },
                    "metadata": {
                        "type": ["object", "null"],
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["id", "nested_items"],
            },
        },
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"$ref": "#/definitions/complex_item"}},
            "description": {"type": ["string", "null"]},
        },
        "required": ["items"],
    }

    # Test resolving the array type with complex nested references
    items_schema = root_schema["properties"]["items"]
    result_type = resolver.resolve_type(items_schema, root_schema)

    from typing import get_args, get_origin

    # The result should be List[dict]
    assert get_origin(result_type) is list
    assert get_args(result_type)[0] is dict

    # Verify we can create and validate a model with this schema
    from json_schema_to_pydantic import create_model

    model = create_model(root_schema)
    instance = model.model_validate(
        {
            "items": [
                {
                    "id": "item1",
                    "nested_items": [
                        {"name": "nested1", "value": 10},
                        {"name": "nested2", "value": 20},
                    ],
                    "metadata": {"key1": "value1", "key2": "value2"},
                },
                {"id": "item2", "nested_items": [{"name": "nested3", "value": 30}]},
            ],
            "description": "A complex nested structure",
        }
    )

    # Verify the structure was correctly parsed
    # Access as dictionary items since they're dictionaries, not models
    assert instance.items[0]["id"] == "item1"
    assert instance.items[0]["nested_items"][0]["name"] == "nested1"
    assert instance.items[0]["nested_items"][0]["value"] == 10
    assert instance.items[0]["metadata"]["key1"] == "value1"
    assert instance.items[1]["id"] == "item2"
    assert instance.items[1]["nested_items"][0]["name"] == "nested3"
    assert instance.items[1]["nested_items"][0]["value"] == 30
    assert instance.description == "A complex nested structure"


def test_type_resolver_anytype():
    """Test handling of anyType."""
    resolver = TypeResolver()
    from typing import Any, Optional

    # Test "anyType"
    schema_any = {"type": "anyType"}
    result_any = resolver.resolve_type(schema_any, {})
    assert result_any is Any

    # Test ["null", "anyType"]
    schema_optional_any = {"type": ["null", "anyType"]}
    result_optional_any = resolver.resolve_type(schema_optional_any, {})
    assert result_optional_any == Optional[Any]

    # Test ["anyType", "null"] (order shouldn't matter)
    schema_optional_any_reversed = {"type": ["anyType", "null"]}
    result_optional_any_reversed = resolver.resolve_type(
        schema_optional_any_reversed, {}
    )
    assert result_optional_any_reversed == Optional[Any]
