from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Union, Type, Tuple, Annotated
from uuid import UUID
from pydantic import create_model, Field


class JsonSchemaToPydantic:
    def __init__(self):
        self.type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": None,
        }

        self.format_mapping = {
            "date-time": datetime,
            "date": date,
            "time": time,
            "email": str,
            "uri": str,
            "uuid": UUID,
        }

    def convert_schema_to_model(
        self, schema: Dict[str, Any], model_name: str = "DynamicModel"
    ):
        """Main entry point to convert JSON schema to Pydantic model.

        This method assumes the input JSON Schema is valid and focuses on
        translating schema constraints into Pydantic validation rules.
        The resulting model will enforce data validation according to the schema rules.
        """
        # Filter out schema metadata fields
        schema = {k: v for k, v in schema.items() if k != "$schema"}

        required = schema.get("required") or []
        fields = self._process_properties(schema.get("properties", {}), required)

        model_config = {}
        # Handle additionalProperties
        if "additionalProperties" in schema and not schema["additionalProperties"]:
            model_config["extra"] = "forbid"

        return self._create_pydantic_model(model_name, fields, required, model_config)

    def _process_properties(
        self, properties: Dict[str, Any], required: List[str] = None
    ) -> Dict[str, Tuple[Type, Any]]:
        """Process schema properties into Pydantic field definitions"""
        fields = {}
        required = required or []

        for field_name, field_schema in properties.items():
            is_required = field_name in required
            field_type, field_info = self._process_field(field_schema, is_required)
            fields[field_name] = (field_type, field_info)

        return fields

    def _process_field(
        self, field_schema: Dict[str, Any], is_required: bool = False
    ) -> Tuple[Type, Any]:
        """Process individual field schema into Pydantic type and field info"""
        field_type = self._get_field_type(field_schema)
        field_info = self._get_field_info(field_schema, is_required)

        return field_type, field_info

    def _get_field_type(self, field_schema: Dict[str, Any]) -> Type:
        """Determine Python/Pydantic type from schema field"""
        # Handle oneOf with discriminated unions
        if "oneOf" in field_schema:
            variants = []
            discriminator = field_schema.get("discriminator", {})
            prop_name = discriminator.get("propertyName", "type")

            for i, schema in enumerate(field_schema["oneOf"]):
                variant_name = f"Variant_{i}_{id(schema)}"
                variant_type = f"variant_{i}"

                # Process original properties
                properties = schema.get("properties", {}).copy()
                required = list(schema.get("required", []))

                # Add discriminator field to properties and required
                if prop_name not in properties:
                    properties[prop_name] = {"type": "string"}
                if prop_name not in required:
                    required.append(prop_name)

                variant_fields = self._process_properties(properties, required)

                # Add discriminator with Literal type
                from typing_extensions import Literal

                variant_fields[prop_name] = (
                    Literal[variant_type],
                    Field(
                        default=variant_type,
                        description=f"Discriminator field for variant {i}",
                    ),
                )

                # Create variant model
                variant_model = create_model(
                    variant_name,
                    **variant_fields,
                )
                variants.append(variant_model)

            # Create discriminated union
            return Annotated[
                Union[tuple(variants)], Field(discriminator=prop_name)  # type: ignore
            ]

        # Handle format first
        if "format" in field_schema:
            format_type = field_schema["format"]
            if format_type in self.format_mapping:
                return self.format_mapping[format_type]

        # Handle enum second
        if "enum" in field_schema:
            from enum import Enum

            return Enum(
                f"DynamicEnum_{id(field_schema)}",
                {str(v): v for v in field_schema["enum"]},
            )

        schema_type = field_schema.get("type")

        if not schema_type:
            return Any

        if isinstance(schema_type, list):
            types = [self.type_mapping[t] for t in schema_type if t != "null"]
            return Union[tuple(types)]  # type: ignore

        if schema_type == "array":
            items = field_schema.get("items", {})
            item_type = self._get_field_type(items)
            # Use Set instead of List for arrays with uniqueItems constraint
            if field_schema.get("uniqueItems", False):
                from typing import Set

                return Set[item_type]
            return List[item_type]

        if schema_type == "object":
            nested_properties = field_schema.get("properties", {})
            nested_required = field_schema.get("required", [])
            nested_fields = self._process_properties(nested_properties)
            return self._create_pydantic_model(
                f"NestedModel_{id(field_schema)}", nested_fields, nested_required
            )

        return self.type_mapping[schema_type]

    def _get_field_info(
        self, field_schema: Dict[str, Any], is_required: bool = False
    ) -> Any:
        """Create Pydantic Field from schema field"""
        field_args = {}

        # Only make non-required fields optional by default
        if "default" not in field_schema and not is_required:
            field_args["default"] = None

        if "minimum" in field_schema:
            field_args["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            field_args["le"] = field_schema["maximum"]
        if "multipleOf" in field_schema:
            field_args["multiple_of"] = field_schema["multipleOf"]
        if "exclusiveMinimum" in field_schema:
            field_args["gt"] = field_schema["exclusiveMinimum"]
        if "exclusiveMaximum" in field_schema:
            field_args["lt"] = field_schema["exclusiveMaximum"]
        if "minLength" in field_schema:
            field_args["min_length"] = field_schema["minLength"]
        if "maxLength" in field_schema:
            field_args["max_length"] = field_schema["maxLength"]
        if "pattern" in field_schema:
            field_args["pattern"] = field_schema["pattern"]
        if "default" in field_schema:
            field_args["default"] = field_schema["default"]
        if "description" in field_schema:
            field_args["description"] = field_schema["description"]

        return Field(**field_args)

    def _create_pydantic_model(
        self,
        name: str,
        fields: Dict[str, Tuple[Type, Any]],
        required: List[str],
        config: Dict[str, Any] = None,
    ):
        """Create Pydantic model from processed fields"""
        processed_fields = {}

        for field_name, (field_type, field_info) in fields.items():
            if field_name not in required:
                processed_fields[field_name] = (Optional[field_type], field_info)
            else:
                processed_fields[field_name] = (field_type, field_info)

        return create_model(name, __config__=config or {}, **processed_fields)
