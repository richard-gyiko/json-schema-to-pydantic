from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Union, Type, Tuple
from uuid import UUID
from pydantic import create_model
from pydantic.fields import FieldInfo

class JsonSchemaToPydantic:
    def __init__(self):
        self.type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": None
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
        self, 
        schema: Dict[str, Any], 
        model_name: str = "DynamicModel"
    ):
        """Main entry point to convert JSON schema to Pydantic model"""
        fields = self._process_properties(schema.get("properties", {}))
        # If required is not specified, all fields are optional
        # If required is specified, only those fields are required
        required = schema.get("required") or []
        
        return self._create_pydantic_model(model_name, fields, required)

    def _process_properties(
        self, 
        properties: Dict[str, Any]
    ) -> Dict[str, Tuple[Type, FieldInfo]]:
        """Process schema properties into Pydantic field definitions"""
        fields = {}
        
        for field_name, field_schema in properties.items():
            field_type, field_info = self._process_field(field_schema)
            fields[field_name] = (field_type, field_info)
            
        return fields

    def _process_field(
        self, 
        field_schema: Dict[str, Any]
    ) -> Tuple[Type, FieldInfo]:
        """Process individual field schema into Pydantic type and field info"""
        field_type = self._get_field_type(field_schema)
        field_info = self._get_field_info(field_schema)
        
        return field_type, field_info

    def _get_field_type(self, field_schema: Dict[str, Any]) -> Type:
        """Determine Python/Pydantic type from schema field"""
        schema_type = field_schema.get("type")
        
        if not schema_type:
            return Any
            
        if isinstance(schema_type, list):
            types = [self.type_mapping[t] for t in schema_type if t != "null"]
            return Union[tuple(types)]  # type: ignore
            
        if schema_type == "array":
            items = field_schema.get("items", {})
            item_type = self._get_field_type(items)
            return List[item_type]
            
        if schema_type == "object":
            nested_properties = field_schema.get("properties", {})
            nested_required = field_schema.get("required", [])
            nested_fields = self._process_properties(nested_properties)
            return self._create_pydantic_model(
                f"NestedModel_{id(field_schema)}", 
                nested_fields, 
                nested_required
            )
            
        return self.type_mapping[schema_type]

    def _get_field_info(self, field_schema: Dict[str, Any]) -> FieldInfo:
        """Create Pydantic FieldInfo from schema field"""
        field_args = {}  # Let required status be handled by _create_pydantic_model
        
        if "minimum" in field_schema:
            field_args["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            field_args["le"] = field_schema["maximum"]
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
            
        return FieldInfo(**field_args)

    def _create_pydantic_model(
        self, 
        name: str, 
        fields: Dict[str, Tuple[Type, FieldInfo]], 
        required: List[str]
    ):
        """Create Pydantic model from processed fields"""
        for field_name, (field_type, field_info) in fields.items():
            if field_name not in required:
                # For optional fields, set default=None in the FieldInfo
                field_info.default = None
                fields[field_name] = (Optional[field_type], field_info)
                
        return create_model(name, **fields)
