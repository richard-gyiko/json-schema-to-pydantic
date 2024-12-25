# MCP AutoGen

A Python library for automatically generating Pydantic models from JSON Schema definitions.

## Features

- Converts JSON Schema to Pydantic v2 models
- Supports complex schema features including:
  - References ($ref)
  - Combiners (allOf, anyOf, oneOf)
  - Type constraints and validations
  - Array and object validations
- Full type hinting support
- Circular reference detection

## Installation

```bash
pip install mcp-autogen
```

## Quick Start

```python
from autogen_mcp_tool_adapter.pydantic_model_builder import PydanticModelBuilder

# Define your JSON Schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name"]
}

# Create the model builder
builder = PydanticModelBuilder()

# Generate your Pydantic model
MyModel = builder.create_pydantic_model(schema)

# Use the model
instance = MyModel(name="John", age=30)
```

## Documentation

See [docs/features.md](docs/features.md) for detailed documentation of supported JSON Schema features.

## License

This project is licensed under the terms of the license included in the repository.
