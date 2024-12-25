from typing import Any, Type, Dict, Union, Annotated, Literal
from typing import List as typing_List
from pydantic import BaseModel, create_model, Field, field_validator
from pydantic.config import ConfigDict


class PydanticModelBuilder:
    def create_pydantic_model(self, schema: dict) -> Type[BaseModel]:
        """Create a Pydantic model from a JSON schema."""
        model_config = ConfigDict(extra="forbid")

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        fields = {}
        for field_name, field_schema in properties.items():
            field_type = self._get_field_type(field_schema)
            field_info = self._get_field_constraints(field_schema)

            if field_name in required:
                field_info.update({"default": ...})

            if isinstance(field_type, tuple):
                actual_type, validators = field_type
                fields[field_name] = (actual_type, Field(**field_info))
            else:
                fields[field_name] = (field_type, Field(**field_info))

        Model = create_model(
            "Model",
            **fields,
            model_config=model_config,
            __validators__=validators if "validators" in locals() else {},
        )
        return Model

    def _get_field_type(self, field_schema: dict) -> Any:
        """Get the Pydantic field type for a JSON schema field."""
        if "enum" in field_schema:
            return Literal[tuple(field_schema["enum"])]

        field_type = field_schema.get("type")

        if field_type == "array":
            items_schema = field_schema.get("items", {})
            item_type = self._get_field_type(items_schema)
            if field_schema.get("uniqueItems", False):
                from typing import Set

                return Set[item_type]
            return typing_List[item_type]

        if field_type == "string":
            return str
        if field_type == "integer":
            return int
        if field_type == "number":
            return float
        if field_type == "boolean":
            return bool
        if field_type == "object":
            return self.create_pydantic_model(field_schema)
        if "oneOf" in field_schema:
            return self._handle_one_of(field_schema)

        if "anyOf" in field_schema:
            return self._handle_any_of(field_schema["anyOf"])

        raise ValueError(f"Unsupported field type: {field_type}")

    def _handle_any_of(self, schemas: list) -> Any:
        """Handle anyOf schema combinator."""
        if not schemas:
            raise ValueError("anyOf must contain at least one schema")

        types = []
        for schema in schemas:
            if not isinstance(schema, dict):
                continue

            schema_type = schema.get("type")
            if schema_type == "object":
                model = self.create_pydantic_model(schema)
                types.append(model)
            elif schema_type == "string":
                types.append(str)
            elif schema_type == "number":
                types.append(float)
            elif schema_type == "integer":
                types.append(int)
            elif schema_type == "boolean":
                types.append(bool)

        if not types:
            raise ValueError("No valid schemas found in anyOf")

        # Create a validator function for this specific anyOf case
        def validate_any_of(cls, v):
            if isinstance(v, bool) and bool not in types:
                raise ValueError("Boolean values are not allowed for this field")

            for t in types:
                try:
                    # Try Pydantic model validation first for dict inputs
                    if isinstance(v, dict) and hasattr(t, "model_validate"):
                        return t.model_validate(v)
                    
                    # Special handling for numeric types
                    if t is float and isinstance(v, (int, float)):
                        return float(v)
                    
                    # Handle primitive types
                    if isinstance(t, type) and isinstance(v, t):
                        return v
                    
                    # Handle existing model instances
                    if isinstance(v, BaseModel) and isinstance(v, t):
                        return v
                except Exception:
                    continue

            allowed_types = [getattr(t, "__name__", str(t)) for t in types]
            raise ValueError(
                f"Value must be one of the following types: {', '.join(allowed_types)}"
            )

        # Create the model with the validator
        validators = {
            "any_of_validator": field_validator("*", mode="before")(validate_any_of)
        }

        return Union[tuple(types)], validators

    def _handle_one_of(self, schema: dict) -> Any:
        """Handle oneOf schema combinator using discriminated unions."""
        one_of = schema.get("oneOf", [])
        if not one_of:
            raise ValueError("oneOf must contain at least one schema")

        # We need to find a common discriminator field across all schemas
        discriminator_field = "type"

        # Create models for each oneOf schema
        models = []
        for i, subschema in enumerate(one_of):
            # Each subschema needs a discriminator field
            if isinstance(subschema, dict):
                # Add the discriminator field if not present
                if "properties" not in subschema:
                    subschema["properties"] = {}

                # Get the discriminator value from the const field
                discriminator_value = (
                    subschema.get("properties", {})
                    .get(discriminator_field, {})
                    .get("const")
                )
                if not discriminator_value:
                    raise ValueError(
                        f"Schema in oneOf must have a '{discriminator_field}' field with a 'const' value"
                    )

                # Create a Literal type for the discriminator field
                subschema["properties"][discriminator_field] = {
                    "type": "string",
                    "enum": [discriminator_value],
                }

                model = self.create_pydantic_model(subschema)
                models.append(model)

        union_types = []
        for model in models:
            union_types.append(model)

        return Annotated[
            Union[tuple(union_types)], Field(discriminator=discriminator_field)
        ]

    def _get_field_constraints(self, field_schema: dict) -> Dict[str, Any]:
        """Extract field constraints from schema."""
        constraints = {}

        # String constraints
        if "minLength" in field_schema:
            constraints["min_length"] = field_schema["minLength"]
        if "maxLength" in field_schema:
            constraints["max_length"] = field_schema["maxLength"]
        if "pattern" in field_schema:
            constraints["pattern"] = field_schema["pattern"]

        # Number constraints
        if "minimum" in field_schema:
            constraints["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            constraints["le"] = field_schema["maximum"]
        if "exclusiveMinimum" in field_schema:
            constraints["gt"] = field_schema["exclusiveMinimum"]
        if "exclusiveMaximum" in field_schema:
            constraints["lt"] = field_schema["exclusiveMaximum"]
        if "multipleOf" in field_schema:
            constraints["multiple_of"] = field_schema["multipleOf"]

        # Array constraints
        if "minItems" in field_schema:
            constraints["min_length"] = field_schema["minItems"]
        if "maxItems" in field_schema:
            constraints["max_length"] = field_schema["maxItems"]

        return constraints
