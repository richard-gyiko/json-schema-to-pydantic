# JSON Schema to Pydantic

A Python library for automatically generating Pydantic v2 models from JSON Schema definitions.

![PyPI - Version](https://img.shields.io/pypi/v/json-schema-to-pydantic)
[![codecov](https://codecov.io/github/richard-gyiko/json-schema-to-pydantic/graph/badge.svg?token=YA2Y769H1K)](https://codecov.io/github/richard-gyiko/json-schema-to-pydantic)

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

## Development Setup

1. Clone the repository
2. Install development dependencies:
```bash
# Using uv (recommended)
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

3. Run tests:
```bash
pytest
```

## Quick Start

```python
from json_schema_to_pydantic import create_model

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
from json_schema_to_pydantic import PydanticModelBuilder

builder = PydanticModelBuilder()
model = builder.create_pydantic_model(schema, root_schema)
```

## Error Handling

The library provides specific exceptions for different error cases:

```python
from json_schema_to_pydantic import (
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

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request

## License

This project is licensed under the terms of the license included in the repository.
