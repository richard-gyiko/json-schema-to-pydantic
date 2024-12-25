# JSON Schema Features Support

This document outlines the JSON Schema features currently supported by the Pydantic Model Builder.

## Basic Types

- `string`
- `integer`
- `number`
- `boolean`
- `array`
- `object`

## String Constraints

- `minLength`: Minimum string length
- `maxLength`: Maximum string length
- `pattern`: Regular expression pattern validation

## Numeric Constraints

- `minimum`: Minimum value (inclusive)
- `maximum`: Maximum value (inclusive)
- `exclusiveMinimum`: Minimum value (exclusive)
- `exclusiveMaximum`: Maximum value (exclusive)
- `multipleOf`: Value must be a multiple of this number

## Array Constraints

- `items`: Schema for array items
- `minItems`: Minimum array length
- `maxItems`: Maximum array length
- `uniqueItems`: Enforces unique items when true

## Object Properties

- `properties`: Object property definitions
- `required`: List of required properties
- `additionalProperties`: Not supported (defaults to False)

## Schema Combiners

### allOf
Combines multiple schemas with AND logic. All constraints from each schema must be satisfied.

Example:
```json
{
    "allOf": [
        {"type": "object", "properties": {"id": {"type": "integer"}}},
        {"type": "object", "properties": {"name": {"type": "string"}}}
    ]
}
```

### anyOf
Allows a value to validate against any of the given schemas.

Example:
```json
{
    "anyOf": [
        {"type": "string"},
        {"type": "number"}
    ]
}
```

### oneOf
Implements discriminated unions using a type field.

Example:
```json
{
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "dog"},
                "bark": {"type": "boolean"}
            }
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "cat"},
                "meow": {"type": "boolean"}
            }
        }
    ]
}
```

## References

- Local references (`#/definitions/...`) are supported
- Circular reference detection
- External references are not currently supported

## Validation Features

- Type validation
- Required fields
- Numeric ranges
- String patterns and length
- Array length and uniqueness
- Enum values
- Const values

## Not Currently Supported

- `$id`
- `$schema`
- `definitions` at root level (though references work)
- External references
- `propertyNames`
- `dependencies`
- `if`/`then`/`else`
- `not`
- `additionalProperties`
- `patternProperties`
