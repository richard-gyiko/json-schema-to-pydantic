from typing import Dict, Any, List, Type, Union, Annotated, Literal, Optional
from pydantic import BaseModel, create_model, Field, Discriminator, RootModel
from .interfaces import ICombinerHandler
from .exceptions import CombinerError
from .builders import ConstraintBuilder
from .resolvers import TypeResolver


class CombinerHandler(ICombinerHandler):
    """Handles JSON Schema combiners (allOf, anyOf, oneOf)"""

    def __init__(self):
        self.constraint_builder = ConstraintBuilder()
        self.type_resolver = TypeResolver()

    def _convert_property(
        self, prop_schema: Dict[str, Any], required_fields: List[str] = None
    ) -> tuple:
        """Convert JSON Schema property to Pydantic field."""
        if required_fields is None:
            required_fields = []

        constraints = self.constraint_builder.build_constraints(prop_schema)
        field_kwargs = {}

        # Handle description
        if "description" in prop_schema:
            field_kwargs["description"] = prop_schema["description"]

        python_type = self.type_resolver.resolve_type(prop_schema, {})

        if isinstance(constraints, type):  # Handle special types like EmailStr
            python_type = constraints
        elif "const" in prop_schema:
            python_type = Literal[prop_schema["const"]]
        else:
            field_kwargs.update(constraints)

        # Handle default values
        if "default" in prop_schema:
            field_kwargs["default"] = prop_schema["default"]
        elif prop_schema.get("name") not in required_fields:
            python_type = Optional[python_type]
            field_kwargs["default"] = None

        return (python_type, Field(**field_kwargs))

    def handle_all_of(
        self, schemas: List[Dict[str, Any]], root_schema: Dict[str, Any]
    ) -> Type[BaseModel]:
        """Combines multiple schemas with AND logic."""
        if not schemas:
            raise CombinerError("allOf must contain at least one schema")

        merged_properties = {}
        required_fields = set()

        for schema in schemas:
            if not isinstance(schema, dict):
                raise CombinerError(f"Invalid schema in allOf: {schema}")

            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for prop_name, prop_schema in properties.items():
                if prop_name in merged_properties:
                    # Merge constraints for existing property
                    merged_properties[prop_name] = (
                        self.constraint_builder.merge_constraints(
                            merged_properties[prop_name], prop_schema
                        )
                    )
                else:
                    merged_properties[prop_name] = prop_schema

            required_fields.update(required)

        # Convert properties to annotated fields
        field_definitions = {
            name: self._convert_property(prop)
            for name, prop in merged_properties.items()
        }

        return create_model(
            "AllOfModel", **field_definitions, model_config={"extra": "forbid"}
        )

    def handle_any_of(
        self, schemas: List[Dict[str, Any]], root_schema: Dict[str, Any]
    ) -> Any:
        """Allows validation against any of the given schemas."""
        if not schemas:
            raise CombinerError("anyOf must contain at least one schema")

        possible_types = []
        for schema in schemas:
            if not isinstance(schema, dict):
                raise CombinerError(f"Invalid schema in anyOf: {schema}")

            if schema.get("type") == "object":
                properties = schema.get("properties", {})
                field_definitions = {
                    name: self._convert_property(prop)
                    for name, prop in properties.items()
                }
                model = create_model(
                    "AnyOfModel", **field_definitions, model_config={"extra": "forbid"}
                )
                possible_types.append(model)
            else:
                possible_types.append(
                    self.type_resolver.resolve_type(schema, root_schema)
                )

        return Union[tuple(possible_types)]

    def handle_one_of(
        self, schema: Dict[str, Any], root_schema: Dict[str, Any]
    ) -> Type[BaseModel]:
        """Implements discriminated unions using a type field."""
        schemas = schema.get("oneOf", [])
        if not schemas:
            raise CombinerError("oneOf must contain at least one schema")

        # Create a model for each variant
        variant_models = {}

        for variant_schema in schemas:
            if not isinstance(variant_schema, dict):
                raise CombinerError(f"Invalid schema in oneOf: {variant_schema}")

            properties = variant_schema.get("properties", {})
            type_const = properties.get("type", {}).get("const")
            if not type_const:
                raise CombinerError("Each oneOf variant must have a type const")

            # Create field definitions for this variant
            fields = {}
            required = variant_schema.get("required", [])

            for name, prop_schema in properties.items():
                if name == "type":
                    description = prop_schema.get("description")
                    fields[name] = (
                        Literal[type_const],
                        Field(default=type_const, description=description),
                    )
                elif "oneOf" in prop_schema:
                    # Handle nested oneOf
                    fields[name] = (
                        self.handle_one_of(prop_schema, root_schema),
                        Field(...),
                    )
                else:
                    field_type, field_info = self._convert_property(
                        prop_schema, required
                    )
                    if name in required:
                        description = prop_schema.get("description")
                        fields[name] = (field_type, Field(..., description=description))
                    else:
                        fields[name] = (field_type, field_info)

            # Create model for this variant
            model_name = f"Variant_{type_const}"
            variant_model = create_model(
                model_name, **fields, model_config={"extra": "forbid"}
            )
            variant_models[type_const] = variant_model

        # Always wrap in RootModel for consistent access pattern
        if len(variant_models) == 1:
            return RootModel[list(variant_models.values())[0]]
        else:
            union_type = Annotated[
                Union[tuple(variant_models.values())],
                Discriminator(discriminator="type"),
            ]
            return RootModel[union_type]
