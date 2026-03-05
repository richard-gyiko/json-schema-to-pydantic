import importlib.metadata

from .exceptions import (
    CombinerError,
    ReferenceError,
    SchemaError,
    TypeError,
)
from .model_builder import PydanticModelBuilder

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
    allow_undefined_type: bool = False,
    populate_by_name: bool = False,
    predefined_models: Optional[Dict[str, Type[BaseModel]]] = None,
    predefined_refs: Optional[Dict[str, Any]] = None,
) -> Type[T]:
    """
    Create a Pydantic model from a JSON Schema.

    Args:
        schema: The JSON Schema to convert
        base_model_type: The base Pydantic model type to use. Defaults to pydantic.BaseModel
        root_schema: The root schema containing definitions.
                    Defaults to schema if not provided.
        allow_undefined_array_items: If True, allows arrays without items schema
        allow_undefined_type: If True, allows schemas without an explicit type
        populate_by_name: If True, allows population of model fields by name and alias
        predefined_models: Optional mapping of local JSON Pointer refs
            (e.g. "#/definitions/MyModel") to existing Pydantic model classes.
            Matching refs are reused instead of generating new model classes.
        predefined_refs: Optional mapping of local JSON Pointer refs
            (e.g. "#/definitions/SomeType") to valid type annotations such as
            list[str], dict[str, int], or TypeAliasType values. Matching refs
            are reused as field types instead of generating new model classes.

    Returns:
        A Pydantic model class

    Raises:
        SchemaError: If the schema is invalid
        TypeError: If an unsupported type is encountered
        CombinerError: If there's an error in schema combiners
        ReferenceError: If there's an error resolving references
    """
    builder = PydanticModelBuilder(
        base_model_type=base_model_type,
        predefined_models=predefined_models,
        predefined_refs=predefined_refs,
    )
    return builder.create_pydantic_model(
        schema,
        root_schema,
        allow_undefined_array_items,
        allow_undefined_type,
        populate_by_name,
    )


__all__ = [
    "create_model",
    "PydanticModelBuilder",
    "SchemaError",
    "TypeError",
    "CombinerError",
    "ReferenceError",
]
