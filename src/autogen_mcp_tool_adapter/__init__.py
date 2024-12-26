from .model_builder import PydanticModelBuilder
from .exceptions import (
    SchemaError,
    TypeError,
    CombinerError,
    ReferenceError,
)

__version__ = "0.1.0"


def create_model(schema: dict, root_schema: dict = None):
    """
    Create a Pydantic model from a JSON Schema.

    Args:
        schema (dict): The JSON Schema to convert
        root_schema (dict, optional): The root schema containing definitions.
                                    Defaults to schema if not provided.

    Returns:
        Type[BaseModel]: A Pydantic model class

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
