from typing import Any, Optional, Type, Dict, TypeVar
from pydantic import BaseModel, create_model, Field

from .builders import ConstraintBuilder
from .resolvers import TypeResolver, ReferenceResolver
from .handlers import CombinerHandler
from .interfaces import IModelBuilder


T = TypeVar("T", bound=BaseModel)


class PydanticModelBuilder(IModelBuilder[T]):
    """Creates Pydantic models from JSON Schema definitions"""

    def __init__(self, base_model_type: Type[T] = BaseModel):
        self.type_resolver = TypeResolver()
        self.constraint_builder = ConstraintBuilder()
        self.reference_resolver = ReferenceResolver()
        self.combiner_handler = CombinerHandler()
        self.base_model_type = base_model_type

    def create_pydantic_model(
        self, schema: Dict[str, Any], root_schema: Optional[Dict[str, Any]] = None
    ) -> Type[T]:
        """
        Creates a Pydantic model from a JSON Schema definition.

        Args:
            schema: The JSON Schema to convert
            root_schema: The root schema containing definitions

        Returns:
            A Pydantic model class
        """
        if root_schema is None:
            root_schema = schema

        # Handle references
        if "$ref" in schema:
            schema = self.reference_resolver.resolve_ref(
                schema["$ref"], schema, root_schema
            )

        # Handle combiners
        if "allOf" in schema:
            return self.combiner_handler.handle_all_of(schema["allOf"], root_schema)
        if "anyOf" in schema:
            return self.combiner_handler.handle_any_of(schema["anyOf"], root_schema)
        if "oneOf" in schema:
            return self.combiner_handler.handle_one_of(schema, root_schema)

        # Get model properties
        title = schema.get("title", "DynamicModel")
        description = schema.get("description")
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Build field definitions
        fields = {}
        for field_name, field_schema in properties.items():
            field_type = self._get_field_type(field_schema, root_schema)
            field_info = self._build_field_info(field_schema, field_name in required)
            fields[field_name] = (field_type, field_info)

        # Create the model
        model = create_model(title, __base__=self.base_model_type, **fields)
        if description:
            model.__doc__ = description

        return model

    def _get_field_type(
        self, field_schema: Dict[str, Any], root_schema: Dict[str, Any]
    ) -> Any:
        """Resolves the Python type for a field schema."""
        if "$ref" in field_schema:
            field_schema = self.reference_resolver.resolve_ref(
                field_schema["$ref"], field_schema, root_schema
            )

        # Handle combiners
        if "allOf" in field_schema:
            return self.combiner_handler.handle_all_of(
                field_schema["allOf"], root_schema
            )
        if "anyOf" in field_schema:
            return self.combiner_handler.handle_any_of(
                field_schema["anyOf"], root_schema
            )
        if "oneOf" in field_schema:
            return self.combiner_handler.handle_one_of(field_schema, root_schema)

        # Handle nested objects by recursively creating models
        if field_schema.get("type") == "object" and "properties" in field_schema:
            return self.create_pydantic_model(field_schema, root_schema)

        return self.type_resolver.resolve_type(field_schema, root_schema)

    def _build_field_info(self, field_schema: Dict[str, Any], required: bool) -> Field:
        """Creates a Pydantic Field with constraints from schema."""
        field_kwargs = {}

        # Add constraints
        constraints = self.constraint_builder.build_constraints(field_schema)
        if isinstance(constraints, type):  # Handle special types like EmailStr
            pass  # Type will be handled by type_resolver
        elif isinstance(constraints, dict):
            field_kwargs.update(constraints)

        # Handle description
        if "description" in field_schema:
            field_kwargs["description"] = field_schema["description"]

        # Handle default value
        if "default" in field_schema:
            field_kwargs["default"] = field_schema["default"]
        elif not required:
            field_kwargs["default"] = None

        return Field(**field_kwargs)
