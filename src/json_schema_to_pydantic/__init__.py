from .exceptions import (
    CombinerError,
    ReferenceError,
    SchemaError,
    TypeError,
)
from .model_builder import PydanticModelBuilder

import importlib.metadata

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development mode


from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def create_model(
    schema: Dict[str, Any],
    base_model_type: Type[T] = BaseModel,
    root_schema: Optional[Dict[str, Any]] = None,
    allow_undefined_array_items: bool = False,
) -> Type[T]:
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
    builder = PydanticModelBuilder(base_model_type=base_model_type)
    return builder.create_pydantic_model(
        schema, root_schema, allow_undefined_array_items
    )


__all__ = [
    "create_model",
    "PydanticModelBuilder",
    "SchemaError",
    "TypeError",
    "CombinerError",
    "ReferenceError",
]
