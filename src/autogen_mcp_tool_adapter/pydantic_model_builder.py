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
            
            if not ref.startswith('#'):
                raise ValueError("Only local references (#/...) are supported")
                
            # Split the reference path and navigate through the schema
            path = ref.split('/')[1:]  # Remove the '#' and split
            current = root_schema
            for part in path:
                # Handle JSON Pointer escaping
                part = part.replace('~1', '/').replace('~0', '~')
                current = current[part]
            return self._get_field_type(current, root_schema)
                
        finally:
            self._processing_refs.remove(ref)

    def create_pydantic_model(self, schema: dict, root_schema: dict = None) -> Type[BaseModel]:
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

    def _get_field_type(self, field_schema: dict, root_schema: dict) -> Any:
        """Get the Pydantic field type for a JSON schema field."""
        if "$ref" in field_schema:
            return self._resolve_ref(field_schema["$ref"], field_schema, root_schema)
            
        if "enum" in field_schema:
            return Literal[tuple(field_schema["enum"])]

        if "allOf" in field_schema:
            return self._handle_all_of(field_schema["allOf"], root_schema)

        field_type = field_schema.get("type")

        if field_type == "array":
            items_schema = field_schema.get("items", {})
            item_type = self._get_field_type(items_schema, root_schema)
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
            return self.create_pydantic_model(field_schema, root_schema)
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

    def _merge_constraints(self, schema1: dict, schema2: dict) -> dict:
        """Merge constraints from two schemas for the same property."""
        merged = schema1.copy()

        # Handle numeric constraints
        for constraint in ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"]:
            if constraint in schema2:
                if constraint in merged:
                    if "minimum" in constraint:
                        merged[constraint] = max(merged[constraint], schema2[constraint])
                    else:
                        merged[constraint] = min(merged[constraint], schema2[constraint])
                else:
                    merged[constraint] = schema2[constraint]

        # Handle string constraints
        for constraint in ["minLength", "maxLength", "pattern"]:
            if constraint in schema2:
                if constraint in merged:
                    if "min" in constraint:
                        merged[constraint] = max(merged[constraint], schema2[constraint])
                    elif "max" in constraint:
                        merged[constraint] = min(merged[constraint], schema2[constraint])
                    else:
                        # For pattern, we could combine them with AND logic
                        merged[constraint] = f"(?={merged[constraint]})(?={schema2[constraint]})"
                else:
                    merged[constraint] = schema2[constraint]

        return merged

    def _handle_all_of(self, schemas: list, root_schema: dict) -> Any:
        """Handle allOf schema combinator."""
        if not schemas:
            raise ValueError("allOf must contain at least one schema")

        # Merge all schemas into a single schema
        merged_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for schema in schemas:
            if not isinstance(schema, dict):
                continue

            if schema.get("type") != "object":
                raise ValueError("allOf only supports object schemas currently")

            # Merge properties
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if prop_name in merged_schema["properties"]:
                    # If property already exists, merge constraints
                    existing_prop = merged_schema["properties"][prop_name]
                    merged_schema["properties"][prop_name] = self._merge_constraints(
                        existing_prop, prop_schema
                    )
                else:
                    merged_schema["properties"][prop_name] = prop_schema

            # Merge required fields
            required = schema.get("required", [])
            merged_schema["required"].extend(required)

        # Remove duplicates from required fields while preserving order
        merged_schema["required"] = list(dict.fromkeys(merged_schema["required"]))

        # Create a model from the merged schema
        return self.create_pydantic_model(merged_schema, root_schema)

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
