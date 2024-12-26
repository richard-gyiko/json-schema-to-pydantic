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
- `email`: `pydantic.EmailStr`
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
- `items`: Schema for array items
- `minItems`/`maxItems`: Array length bounds
- `uniqueItems`: Enforces unique items

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

Local references are supported with circular reference detection:
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

## Limitations

- External references are not supported
- `additionalProperties` defaults to False
- `patternProperties` not supported
- `if`/`then`/`else` not supported
