# JSON Schema Features Support

This document outlines the JSON Schema features supported by the library.

## Basic Types

- `string`: Maps to Python `str`
- `integer`: Maps to Python `int`
- `number`: Maps to Python `float`
- `boolean`: Maps to Python `bool`
- `array`: Maps to Python `List`
- `object`: Maps to Pydantic model

### Multiple Types

JSON Schema allows specifying multiple types for a field using an array. The library handles these cases:

- Single type with `null`: Maps to `Optional[Type]`
  ```json
  {"type": ["string", "null"]}  // → Optional[str]
  ```

- Multiple types without `null`: Maps to `Union[Type1, Type2, ...]`
  ```json
  {"type": ["string", "integer"]}  // → Union[str, int]
  ```

- Multiple types with `null`: Maps to `Optional[Union[Type1, Type2, ...]]`
  ```json
  {"type": ["string", "integer", "null"]}  // → Optional[Union[str, int]]
  ```

Example with complex types:
```json
{
    "type": "object",
    "properties": {
        "flexible_field": {
            "type": ["string", "integer", "boolean"]
        },
        "optional_flexible": {
            "type": ["array", "string", "null"],
            "items": {"type": "integer"}
        }
    }
}
```

## String Formats

Supported formats with their Python types:
- `date-time`: `datetime.datetime`
- `uri`: `pydantic.AnyUrl`
- `uuid`: `uuid.UUID`

Example:
```json
{
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email"},
        "website": {"type": "string", "format": "uri"},
        "created_at": {"type": "string", "format": "date-time"}
    }
}
```

## Constraints

### String Constraints
- `minLength`: Minimum string length
- `maxLength`: Maximum string length
- `pattern`: Regular expression pattern
- `const`: Fixed value

### Numeric Constraints
- `minimum`/`maximum`: Inclusive bounds
- `exclusiveMinimum`/`exclusiveMaximum`: Exclusive bounds
- `multipleOf`: Value must be multiple of this number

### Array Constraints
- `items`: Schema for array items. By default, this is required for arrays.
- `minItems`/`maxItems`: Array length bounds
- `uniqueItems`: Enforces unique items

### Handling Arrays Without `items`

By default, the library requires arrays to have an `items` schema defined. However, some schemas might omit this. You can allow arrays without a defined `items` schema by passing `allow_undefined_array_items=True` to `create_model` or `PydanticModelBuilder.create_pydantic_model`. When enabled, such arrays will be typed as `List[Any]`.

```python
from json_schema_to_pydantic import create_model

# Schema with an array lacking 'items'
schema = {"type": "object", "properties": {"mixed_tags": {"type": "array"}}}

# This would raise a TypeError by default
# model = create_model(schema)

# Allow arrays without 'items'
RelaxedModel = create_model(schema, allow_undefined_array_items=True)

# The field 'mixed_tags' will be List[Any]
instance = RelaxedModel(mixed_tags=[1, "string", True, None])
```

## Schema Combiners

### allOf
Combines multiple schemas with AND logic:
```json
{
    "allOf": [
        {"type": "object", "properties": {"id": {"type": "integer"}}},
        {"type": "object", "properties": {"name": {"type": "string"}}}
    ]
}
```

### oneOf
Creates discriminated unions using a type field:
```json
{
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "user"},
                "email": {"type": "string", "format": "email"}
            }
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "admin"},
                "permissions": {"type": "array", "items": {"type": "string"}}
            }
        }
    ]
}
```

## References

Local references (`$ref`) are supported, including within `allOf`, `anyOf`, and `oneOf` combiners. References can be used in any schema location, including as array items and within nested structures. Circular reference detection is also implemented.

Example:
```json
{
    "type": "object",
    "properties": {
        "parent": {"$ref": "#/definitions/Node"}
    },
    "definitions": {
        "Node": {
            "type": "object",
            "properties": {
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Node"}
                }
            }
        }
    }
}
```

Example with nested references in array items:
```json
{
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {"$ref": "#/definitions/ComplexItem"}
        }
    },
    "definitions": {
        "NestedItem": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "integer"}
            }
        },
        "ComplexItem": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "nested_items": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/NestedItem"}
                }
            }
        }
    }
}
```

## Limitations

- External references are not supported
- `additionalProperties` defaults to False
- `patternProperties` not supported
- `if`/`then`/`else` not supported

## Top-Level Arrays and Scalars

The library supports schemas where the root type is not an object. This includes arrays and scalar types.

### Top-Level Arrays

Schemas with `"type": "array"` at the root are converted to Pydantic `RootModel`:

```python
from json_schema_to_pydantic import create_model

schema = {
    "type": "array",
    "items": {"type": "string"}
}

StringList = create_model(schema)
instance = StringList(["a", "b", "c"])
print(instance.root)  # ['a', 'b', 'c']
```

### Scalar Root Types

Schemas with scalar types (`string`, `integer`, `number`, `boolean`) at the root are also supported:

```python
schema = {"type": "integer", "minimum": 0}
PositiveInt = create_model(schema)
instance = PositiveInt(42)
print(instance.root)  # 42
```

## Underscore-Prefixed Fields

JSON schemas from OpenAPI specs often contain fields starting with underscores (e.g., `_links`, `_embedded`). Since Pydantic doesn't allow field names starting with `_`, the library automatically:

1. Strips the leading underscore from the field name
2. Adds the original name as an alias
3. Optionally enables `populate_by_name` for flexible instantiation

```python
from json_schema_to_pydantic import create_model

schema = {
    "type": "object",
    "properties": {
        "_name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["_name"]
}

# With populate_by_name=True, you can use either name
Model = create_model(schema, populate_by_name=True)

# Both of these work:
instance1 = Model(_name="John", age=30)  # Using alias (original name)
instance2 = Model(name="John", age=30)   # Using field name

# Serialization preserves the original names
print(instance1.model_dump(by_alias=True))  # {"_name": "John", "age": 30}
```

### Collision Detection

If sanitizing a field name would create a duplicate (e.g., both `_name` and `name` exist), a `SchemaError` is raised:

```python
schema = {
    "type": "object",
    "properties": {
        "_name": {"type": "string"},
        "name": {"type": "string"}  # Collision!
    }
}

# Raises SchemaError: Duplicate field name after sanitization: 'name'
Model = create_model(schema)
```

### Combiner Support

Underscore field handling works with all schema combiners (`allOf`, `anyOf`, `oneOf`):

```python
schema = {
    "allOf": [
        {"type": "object", "properties": {"_id": {"type": "string"}}},
        {"type": "object", "properties": {"name": {"type": "string"}}}
    ]
}

Model = create_model(schema, populate_by_name=True)
instance = Model(_id="123", name="Test")
print(instance.id)  # "123"
```
