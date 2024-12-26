from typing import Any, Type, Dict, Union, Annotated, Literal
from typing import List as typing_List
from pydantic import BaseModel, create_model, Field, field_validator
from pydantic.config import ConfigDict


class PydanticModelBuilder:
    def __init__(self):
        self._processing_refs: set[str] = set()  # For circular reference detection

    def _resolve_ref(self, ref: str, schema: dict, root_schema: dict) -> Any:
        """Resolve a JSON Schema $ref."""
        if ref in self._processing_refs:
            raise ValueError(f"Circular reference detected: {ref}")

        try:
            self._processing_refs.add(ref)

            if not ref.startswith("#"):
                raise ValueError("Only local references (#/...) are supported")

            # Split the reference path and navigate through the schema
            path = ref.split("/")[1:]  # Remove the '#' and split
            current = root_schema
            for part in path:
                # Handle JSON Pointer escaping
                part = part.replace("~1", "/").replace("~0", "~")
                current = current[part]
            return self._get_field_type(current, root_schema)

        finally:
            self._processing_refs.remove(ref)

    def create_pydantic_model(
        self, schema: dict, root_schema: dict = None
    ) -> Type[BaseModel]:
        """Create a Pydantic model from a JSON schema."""
        if root_schema is None:
            root_schema = schema

        model_config = ConfigDict(extra="forbid")

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        fields = {}
        for field_name, field_schema in properties.items():
            field_type = self._get_field_type(field_schema, root_schema)
            field_info = self._get_field_constraints(field_schema)

            if isinstance(field_type, tuple):
                actual_type, validators = field_type
                fields[field_name] = (
                    actual_type,
                    Field(
                        **field_info, default=... if field_name in required else None
                    ),
                )
            elif isinstance(field_info, type):  # Handle format types directly
                fields[field_name] = (
                    field_info,
                    Field(default=... if field_name in required else None),
                )
            else:
                fields[field_name] = (
                    field_type,
                    Field(
                        **field_info, default=... if field_name in required else None
                    ),
                )

        Model = create_model(
            "Model",
            **fields,
            model_config=model_config,
            __validators__=validators if "validators" in locals() else {},
        )
        return Model

    def _get_field_type(self, field_schema: dict, root_schema: dict) -> Any:
        """Get the Pydantic field type for a JSON schema field."""
        if not isinstance(field_schema, dict):
            raise ValueError(f"Invalid schema: expected dict, got {type(field_schema)}")

        if "$ref" in field_schema:
            try:
                return self._resolve_ref(
                    field_schema["$ref"], field_schema, root_schema
                )
            except Exception as e:
                raise ValueError(f"Failed to resolve reference: {str(e)}")

        if "const" in field_schema:
            return Literal[field_schema["const"]]

        if "enum" in field_schema:
            if not field_schema["enum"]:
                raise ValueError("Enum must have at least one value")
            return Literal[tuple(field_schema["enum"])]

        if "allOf" in field_schema:
            try:
                return self._handle_all_of(field_schema["allOf"], root_schema)
            except Exception as e:
                raise ValueError(f"Failed to process allOf: {str(e)}")

        field_type = field_schema.get("type")

        if field_type == "array":
            items_schema = field_schema.get("items")
            if not items_schema:
                raise ValueError("Array type must specify 'items' schema")
            try:
                item_type = self._get_field_type(items_schema, root_schema)
                if field_schema.get("uniqueItems", False):
                    from typing import Set

                    def validate_unique_items(v):
                        if isinstance(v, list):  # Only validate lists
                            if len(v) != len(set(v)):
                                raise ValueError("Array items must be unique")
                        return v

                    validators = {
                        "unique_items_validator": field_validator("*", mode="before")(
                            validate_unique_items
                        )
                    }
                    return Set[item_type], validators
                return typing_List[item_type]
            except Exception as e:
                raise ValueError(f"Failed to process array items: {str(e)}")

        if field_type == "string":
            return str
        if field_type == "integer":
            return int
        if field_type == "number":
            return float
        if field_type == "boolean":
            return bool
        if field_type == "object":
            try:
                return self.create_pydantic_model(field_schema, root_schema)
            except Exception as e:
                raise ValueError(f"Failed to create nested model: {str(e)}")
        if "oneOf" in field_schema:
            try:
                return self._handle_one_of(field_schema)
            except Exception as e:
                raise ValueError(f"Failed to process oneOf: {str(e)}")

        if "anyOf" in field_schema:
            try:
                return self._handle_any_of(field_schema["anyOf"])
            except Exception as e:
                raise ValueError(f"Failed to process anyOf: {str(e)}")

        if not field_type:
            raise ValueError(
                "Schema must specify a 'type' or a combiner ('allOf', 'anyOf', 'oneOf')"
            )

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

    def _merge_constraints(self, schema1: dict, schema2: dict) -> dict:
        """Merge constraints from two schemas for the same property."""
        merged = schema1.copy()

        # Handle numeric constraints
        for constraint in [
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "multipleOf",
        ]:
            if constraint in schema2:
                if constraint in merged:
                    if "minimum" in constraint:
                        merged[constraint] = max(
                            merged[constraint], schema2[constraint]
                        )
                    else:
                        merged[constraint] = min(
                            merged[constraint], schema2[constraint]
                        )
                else:
                    merged[constraint] = schema2[constraint]

        # Handle string constraints
        for constraint in ["minLength", "maxLength", "pattern"]:
            if constraint in schema2:
                if constraint in merged:
                    if "min" in constraint:
                        merged[constraint] = max(
                            merged[constraint], schema2[constraint]
                        )
                    elif "max" in constraint:
                        merged[constraint] = min(
                            merged[constraint], schema2[constraint]
                        )
                    else:
                        # For pattern, we could combine them with AND logic
                        merged[constraint] = (
                            f"(?={merged[constraint]})(?={schema2[constraint]})"
                        )
                else:
                    merged[constraint] = schema2[constraint]

        return merged

    def _handle_all_of(self, schemas: list, root_schema: dict) -> Any:
        """Handle allOf schema combinator."""
        if not schemas:
            raise ValueError("allOf must contain at least one schema")

        # Get the common type from schemas if present
        schema_types = {
            schema.get("type")
            for schema in schemas
            if isinstance(schema, dict) and "type" in schema
        }
        if len(schema_types) > 1:
            raise ValueError(
                "All schemas in allOf must have the same type if specified"
            )

        common_type = next(iter(schema_types)) if schema_types else None

        if common_type == "object":
            # Handle object type allOf
            merged_schema = {"type": "object", "properties": {}, "required": []}

            for schema in schemas:
                if not isinstance(schema, dict):
                    continue

                # Merge properties
                properties = schema.get("properties", {})
                for prop_name, prop_schema in properties.items():
                    if prop_name in merged_schema["properties"]:
                        existing_prop = merged_schema["properties"][prop_name]
                        merged_schema["properties"][prop_name] = (
                            self._merge_constraints(existing_prop, prop_schema)
                        )
                    else:
                        merged_schema["properties"][prop_name] = prop_schema

                # Merge required fields
                required = schema.get("required", [])
                merged_schema["required"].extend(required)

            # Remove duplicates from required fields while preserving order
            merged_schema["required"] = list(dict.fromkeys(merged_schema["required"]))

            return self.create_pydantic_model(merged_schema, root_schema)
        else:
            # Handle primitive type allOf by merging constraints
            merged_schema = {}
            if common_type:
                merged_schema["type"] = common_type

            for schema in schemas:
                if not isinstance(schema, dict):
                    continue

                # Handle nested combiners
                if "anyOf" in schema:
                    anyof_type = self._handle_any_of(schema["anyOf"])
                    if isinstance(anyof_type, tuple):
                        merged_schema.update({"anyOf": schema["anyOf"]})
                        continue

                # Merge all constraints
                for key, value in schema.items():
                    if key == "type":
                        continue
                    if key in merged_schema:
                        if key in ["minimum", "minLength", "minItems"]:
                            merged_schema[key] = max(merged_schema[key], value)
                        elif key in ["maximum", "maxLength", "maxItems"]:
                            merged_schema[key] = min(merged_schema[key], value)
                        elif key == "pattern":
                            # Combine patterns with positive lookahead
                            merged_schema[key] = f"(?={merged_schema[key]})(?={value})"
                        elif key == "multipleOf":
                            # Find least common multiple
                            from math import lcm

                            merged_schema[key] = lcm(merged_schema[key], value)
                    else:
                        merged_schema[key] = value

            # For primitive types, return the type with merged constraints
            field_type = self._get_field_type(merged_schema, root_schema)
            field_info = self._get_field_constraints(merged_schema)

            if isinstance(field_type, tuple):
                return field_type
            else:
                return (field_type, field_info)

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
        if "format" in field_schema:
            format_type = field_schema["format"]
            if format_type == "email":
                from pydantic import EmailStr

                return EmailStr
            elif format_type == "date-time":
                from datetime import datetime

                return datetime
            elif format_type == "uri":
                from pydantic import AnyUrl

                return AnyUrl
            elif format_type == "uuid":
                from uuid import UUID

                return UUID

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
