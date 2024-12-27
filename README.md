# MCP AutoGen

A Python library for automatically generating Pydantic v2 models from JSON Schema definitions.

## Features

- Converts JSON Schema to Pydantic v2 models
- Supports complex schema features including:
  - References ($ref) with circular reference detection
  - Combiners (allOf, anyOf, oneOf) with proper type discrimination
  - Type constraints and validations
  - Array and object validations
  - Format validations (email, uri, uuid, date-time)
- Full type hinting support
- Clean, simple API

## Installation

```bash
pip install json-schema-to-pydantic
```

## Quick Start

```python
from jsonschema_pydantic import create_model

# Define your JSON Schema
schema = {
    "title": "User",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name", "email"]
}

# Generate your Pydantic model
UserModel = create_model(schema)

# Use the model
user = UserModel(
    name="John Doe",
    email="john@example.com",
    age=30
)
```

## Advanced Usage

For more complex scenarios, you can use the `PydanticModelBuilder` directly:

```python
from jsonschema_pydantic import PydanticModelBuilder

builder = PydanticModelBuilder()
model = builder.create_pydantic_model(schema, root_schema)
```

## Error Handling

The library provides specific exceptions for different error cases:

```python
from jsonschema_pydantic import (
    SchemaError,     # Base class for all schema errors
    TypeError,       # Invalid or unsupported type
    CombinerError,   # Error in schema combiners
    ReferenceError,  # Error in schema references
)

try:
    model = create_model(schema)
except TypeError as e:
    print(f"Invalid type in schema: {e}")
except ReferenceError as e:
    print(f"Invalid reference: {e}")
```

## Documentation

See [docs/features.md](docs/features.md) for detailed documentation of supported JSON Schema features.

## License

This project is licensed under the terms of the license included in the repository.
