from typing import Dict, Any, Set
from .interfaces import ISchemaValidator
from .exceptions import ValidationError


class SchemaValidator(ISchemaValidator):
    """Validates JSON Schema structure and constraints"""

    VALID_TYPES = {"string", "number", "integer", "boolean", "array", "object"}
    VALID_STRING_FORMATS = {"email", "date-time", "uri", "uuid"}

    def __init__(self):
        self._processing_schemas: Set[int] = set()

    def validate_schema(self, schema: Dict[str, Any]) -> None:
        """Validates the structure and constraints of a JSON schema."""
        if not isinstance(schema, dict):
            raise ValidationError("Schema must be a dictionary")

        # Detect circular references
        schema_id = id(schema)
        if schema_id in self._processing_schemas:
            raise ValidationError("Circular schema reference detected")

        try:
            self._processing_schemas.add(schema_id)
            self._validate_schema_structure(schema)
        finally:
            self._processing_schemas.remove(schema_id)

    def _validate_schema_structure(self, schema: Dict[str, Any]) -> None:
        """Validates the internal structure of a schema."""
        # Validate type
        if "type" in schema:
            if schema["type"] not in self.VALID_TYPES:
                raise ValidationError(f"Invalid type: {schema['type']}")

            # Type-specific validation
            if schema["type"] == "array":
                self._validate_array_schema(schema)
            elif schema["type"] == "object":
                self._validate_object_schema(schema)
            elif schema["type"] == "string":
                self._validate_string_schema(schema)
            elif schema["type"] in {"number", "integer"}:
                self._validate_numeric_schema(schema)

        # Validate combiners
        if "allOf" in schema:
            self._validate_combiner(schema["allOf"], "allOf")
        if "anyOf" in schema:
            self._validate_combiner(schema["anyOf"], "anyOf")
        if "oneOf" in schema:
            self._validate_combiner(schema["oneOf"], "oneOf")

    def _validate_array_schema(self, schema: Dict[str, Any]) -> None:
        """Validates array-specific constraints."""
        if "items" not in schema:
            raise ValidationError("Array type must specify 'items' schema")

        if not isinstance(schema["items"], dict):
            raise ValidationError("Items schema must be an object")

        self.validate_schema(schema["items"])

        # Validate array constraints
        if "minItems" in schema and not isinstance(schema["minItems"], int):
            raise ValidationError("minItems must be an integer")

        if "maxItems" in schema and not isinstance(schema["maxItems"], int):
            raise ValidationError("maxItems must be an integer")

        if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
            raise ValidationError("uniqueItems must be a boolean")

    def _validate_object_schema(self, schema: Dict[str, Any]) -> None:
        """Validates object-specific constraints."""
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise ValidationError("Properties must be an object")

        # Validate each property
        for prop_name, prop_schema in properties.items():
            self.validate_schema(prop_schema)

        # Validate required fields
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise ValidationError("Required must be an array")

        if not all(isinstance(field, str) for field in required):
            raise ValidationError("Required field names must be strings")

        if not all(field in properties for field in required):
            raise ValidationError("Required field not found in properties")

    def _validate_string_schema(self, schema: Dict[str, Any]) -> None:
        """Validates string-specific constraints."""
        if "format" in schema and schema["format"] not in self.VALID_STRING_FORMATS:
            raise ValidationError(f"Invalid string format: {schema['format']}")

        if "pattern" in schema and not isinstance(schema["pattern"], str):
            raise ValidationError("Pattern must be a string")

        if "minLength" in schema and not isinstance(schema["minLength"], int):
            raise ValidationError("minLength must be an integer")

        if "maxLength" in schema and not isinstance(schema["maxLength"], int):
            raise ValidationError("maxLength must be an integer")

    def _validate_numeric_schema(self, schema: Dict[str, Any]) -> None:
        """Validates numeric-specific constraints."""
        numeric_constraints = [
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "multipleOf",
        ]

        for constraint in numeric_constraints:
            if constraint in schema:
                if not isinstance(schema[constraint], (int, float)):
                    raise ValidationError(f"{constraint} must be a number")

        if "multipleOf" in schema and schema["multipleOf"] <= 0:
            raise ValidationError("multipleOf must be greater than 0")

    def _validate_combiner(self, schemas: Any, combiner_type: str) -> None:
        """Validates combiner schemas."""
        if not isinstance(schemas, list):
            raise ValidationError(f"{combiner_type} must be an array")

        if not schemas:
            raise ValidationError(f"{combiner_type} must contain at least one schema")

        for sub_schema in schemas:
            self.validate_schema(sub_schema)
