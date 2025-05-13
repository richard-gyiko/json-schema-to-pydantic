# JSON Schema Features Support

This document outlines the JSON Schema features supported by the library.

## Basic Types

- `string`: Maps to Python `str`
- `integer`: Maps to Python `int`
- `number`: Maps to Python `float`
- `boolean`: Maps to Python `bool`
- `array`: Maps to Python `List`
- `object`: Maps to Pydantic model

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
