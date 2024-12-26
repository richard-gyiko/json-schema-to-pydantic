from .model_builder import PydanticModelBuilder
from .exceptions import (
    SchemaError,
    TypeError,
    CombinerError,
    ReferenceError,
)

__version__ = "0.1.0"


from typing import Type, Optional, Dict, Any
from pydantic import BaseModel


def create_model(
    schema: Dict[str, Any], root_schema: Optional[Dict[str, Any]] = None
) -> Type[BaseModel]:
    """
    Create a Pydantic model from a JSON Schema.

    Args:
        schema: The JSON Schema to convert
        root_schema: The root schema containing definitions.
                    Defaults to schema if not provided.

    Returns:
        A Pydantic model class

    Raises:
        SchemaError: If the schema is invalid
        TypeError: If an unsupported type is encountered
        CombinerError: If there's an error in schema combiners
        ReferenceError: If there's an error resolving references
    """
    builder = PydanticModelBuilder()
    return builder.create_pydantic_model(schema, root_schema)


__all__ = [
    "create_model",
    "PydanticModelBuilder",
    "SchemaError",
    "TypeError",
    "CombinerError",
    "ReferenceError",
]
