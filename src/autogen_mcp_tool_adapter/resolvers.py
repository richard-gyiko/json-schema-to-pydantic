from typing import Any, Set, Optional
from datetime import datetime
from pydantic import EmailStr, AnyUrl
from uuid import UUID
from .interfaces import ITypeResolver, IReferenceResolver
from .exceptions import TypeError, ReferenceError


class TypeResolver(ITypeResolver):
    """Resolves JSON Schema types to Pydantic types"""

    def resolve_type(self, schema: dict, root_schema: dict) -> Any:
        """Get the Pydantic field type for a JSON schema field."""
        if not isinstance(schema, dict):
            raise TypeError(f"Invalid schema: expected dict, got {type(schema)}")

        if "const" in schema:
            from typing import Literal

            if schema["const"] is None:
                return Optional[Any]
            return Literal[schema["const"]]

        if schema.get("type") == "null":
            return Optional[Any]

        # Handle array of types (e.g. ["string", "null"])
        if isinstance(schema.get("type"), list):
            types = schema["type"]
            if "null" in types:
                other_types = [t for t in types if t != "null"]
                if len(other_types) == 1:
                    return Optional[
                        self.resolve_type({"type": other_types[0]}, root_schema)
                    ]
            raise TypeError("Unsupported type combination")

        if "enum" in schema:
            if not schema["enum"]:
                raise TypeError("Enum must have at least one value")
            from typing import Literal

            return Literal[tuple(schema["enum"])]

        schema_type = schema.get("type")
        if not schema_type:
            raise TypeError("Schema must specify a type")

        if schema_type == "array":
            items_schema = schema.get("items")
            if not items_schema:
                raise TypeError("Array type must specify 'items' schema")

            item_type = self.resolve_type(items_schema, root_schema)
            if schema.get("uniqueItems", False):
                from typing import Set

                return Set[item_type]
            from typing import List

            return List[item_type]

        # Handle format for string types
        if schema_type == "string" and "format" in schema:
            format_type = schema["format"]
            format_map = {
                "date-time": datetime,
                "email": EmailStr,
                "uri": AnyUrl,
                "uuid": UUID,
            }
            return format_map.get(format_type, str)

        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,  # Will be replaced with actual model in builder
        }

        return type_map.get(schema_type, str)


class ReferenceResolver(IReferenceResolver):
    """Resolves JSON Schema references"""

    def __init__(self):
        self._processing_refs: Set[str] = set()

    def resolve_ref(self, ref: str, schema: dict, root_schema: dict) -> Any:
        """Resolve a JSON Schema $ref."""
        if not ref.startswith("#"):
            raise ReferenceError("Only local references (#/...) are supported")

        if ref in self._processing_refs:
            raise ReferenceError(f"Circular reference detected: {ref}")

        self._processing_refs.add(ref)
        try:
            # Split the reference path and navigate through the schema
            path = ref.split("/")[1:]  # Remove the '#' and split
            current = root_schema

            # Navigate through the schema
            for part in path:
                # Handle JSON Pointer escaping
                part = part.replace("~1", "/").replace("~0", "~")
                try:
                    current = current[part]
                except KeyError:
                    raise ReferenceError(f"Invalid reference path: {ref}")

            # If we find another reference, resolve it
            if isinstance(current, dict):
                if "$ref" in current:
                    current = self.resolve_ref(current["$ref"], current, root_schema)
                elif "properties" in current:
                    # Check properties for references
                    properties = current["properties"]
                    for prop_name, prop_schema in properties.items():
                        if isinstance(prop_schema, dict) and "$ref" in prop_schema:
                            # This will trigger circular reference detection if needed
                            properties[prop_name] = self.resolve_ref(
                                prop_schema["$ref"], prop_schema, root_schema
                            )

            return current
        finally:
            self._processing_refs.remove(ref)
