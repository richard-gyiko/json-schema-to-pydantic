from pydantic import BaseModel, Field, create_model
from typing import Any, Annotated, Type


class PydanticModelBuilder:
    """
    A class to encapsulate the logic for dynamically creating Pydantic models from JSON Schema.
    """

    @staticmethod
    def map_json_type_with_annotated_constraints(schema: dict) -> Any:
        """
        Map JSON Schema types to Python types with constraints.
        """
        json_type = schema.get("type")

        if json_type == "string":
            return Annotated[
                str,
                Field(
                    min_length=schema.get("minLength"),
                    max_length=schema.get("maxLength"),
                    pattern=schema.get("pattern"),
                    description=schema.get("description", "String field"),
                ),
            ]

        elif json_type in ["integer", "number"]:
            return Annotated[
                int if json_type == "integer" else float,
                Field(
                    gt=schema.get("exclusiveMinimum"),
                    ge=schema.get("minimum"),
                    lt=schema.get("exclusiveMaximum"),
                    le=schema.get("maximum"),
                    description=schema.get("description", "Numeric field"),
                ),
            ]

        elif json_type == "array":
            items = (
                PydanticModelBuilder.map_json_type_with_annotated_constraints(
                    schema["items"]
                )
                if "items" in schema
                else Any
            )
            return Annotated[
                list[items],
                Field(
                    min_items=schema.get("minItems"),
                    max_items=schema.get("maxItems"),
                    description=schema.get("description", "Array field"),
                ),
            ]

        elif json_type == "object":
            return PydanticModelBuilder.handle_combinators(schema)

        return Any  # Default fallback for unsupported or missing types

    @staticmethod
    def handle_combinators(schema: dict) -> Any:
        """Handle JSON Schema combinators with proper validation."""
        # Base case: handle simple types and non-combinator objects directly
        if "type" in schema:
            if schema["type"] != "object":
                return PydanticModelBuilder.map_json_type_with_annotated_constraints(schema)
            elif not any(key in schema for key in ["anyOf", "oneOf", "allOf"]):
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                fields = {
                    prop: (
                        PydanticModelBuilder.map_json_type_with_annotated_constraints(details),
                        Field(default=... if prop in required else None)
                    )
                    for prop, details in properties.items()
                }
                return create_model(f"NestedModel_{id(schema)}", **fields)
        if "allOf" in schema:
            sub_schemas = schema["allOf"]
            
            def validate_all_of(value: Any) -> Any:
                if not isinstance(value, dict):
                    raise ValueError("allOf requires an object value")
                
                for sub_schema in sub_schemas:
                    try:
                        if "properties" in sub_schema:
                            props = sub_schema.get("properties", {})
                            req = sub_schema.get("required", [])
                            temp_model = create_model(
                                f"TempModel_{id(sub_schema)}",
                                **{
                                    k: (PydanticModelBuilder.map_json_type_with_annotated_constraints(v), 
                                       Field(default=... if k in req else None))
                                    for k, v in props.items()
                                }
                            )
                            temp_model(**value)
                    except Exception as e:
                        raise ValueError(f"Failed to validate against schema: {str(e)}")
                return value

            return Annotated[Any, Field(validate=validate_all_of)]

        if "oneOf" in schema:
            sub_schemas = schema["oneOf"]

            def validate_one_of(value: Any) -> Any:
                matches = 0
                last_valid = None
                for sub_schema in sub_schemas:
                    try:
                        if sub_schema.get("type") == "object":
                            if not isinstance(value, dict):
                                continue
                            props = sub_schema.get("properties", {})
                            req = sub_schema.get("required", [])
                            temp_model = create_model(
                                f"TempModel_{id(sub_schema)}",
                                **{
                                    k: (PydanticModelBuilder.map_json_type_with_annotated_constraints(v), 
                                       Field(default=... if k in req else None))
                                    for k, v in props.items()
                                }
                            )
                            temp_model(**value)
                            matches += 1
                            last_valid = value
                        else:
                            field_type = PydanticModelBuilder.map_json_type_with_annotated_constraints(
                                sub_schema
                            )
                            field_type(value)
                            matches += 1
                            last_valid = value
                    except Exception:
                        continue
                if matches != 1:
                    raise ValueError(f"Value must match exactly one schema in `oneOf`. Matched: {matches}")
                return last_valid

            return Annotated[Any, Field(validate=validate_one_of)]

        if "anyOf" in schema:
            sub_schemas = schema["anyOf"]

            def validate_any_of(value: Any) -> Any:
                # First check if value type is allowed
                allowed_types = set()
                for sub_schema in sub_schemas:
                    if "type" in sub_schema:
                        allowed_types.add(sub_schema["type"])
                
                value_type = type(value).__name__
                if value_type == "bool":
                    value_type = "boolean"
                elif value_type == "int":
                    value_type = "integer"
                elif value_type == "float":
                    value_type = "number"
                
                if value_type not in allowed_types and "object" not in allowed_types:
                    raise ValueError(f"Invalid type: {value_type}. Must be one of: {allowed_types}")

                for sub_schema in sub_schemas:
                    try:
                        if sub_schema.get("type") == "object":
                            if not isinstance(value, dict):
                                continue
                            props = sub_schema.get("properties", {})
                            req = sub_schema.get("required", [])
                            temp_model = create_model(
                                f"TempModel_{id(sub_schema)}",
                                **{
                                    k: (PydanticModelBuilder.map_json_type_with_annotated_constraints(v), 
                                       Field(default=... if k in req else None))
                                    for k, v in props.items()
                                }
                            )
                            temp_model(**value)
                            return value
                        else:
                            field_type = PydanticModelBuilder.map_json_type_with_annotated_constraints(
                                sub_schema
                            )
                            field_type(value)
                            return value
                    except Exception:
                        continue
                raise ValueError("Value must match at least one schema in `anyOf`")

            return Annotated[Any, Field(validate=validate_any_of)]

        # Fallback for properties without combinators
        return PydanticModelBuilder.map_json_type_with_annotated_constraints(schema)

    @staticmethod
    def create_pydantic_model(schema: dict) -> Type[BaseModel]:
        """Generate a Pydantic model from a JSON Schema."""
        try:
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            fields = {}
            
            for prop, details in properties.items():
                field_type = PydanticModelBuilder.handle_combinators(details)
                field_info = Field(default=... if prop in required else None)
                fields[prop] = (field_type, field_info)

            # Create a base model with the fields
            base_model = create_model(schema.get("title", "DynamicModel"), **fields)
            
            # Create a wrapper model that converts ValidationError to ValueError
            class ValidatedModel(base_model):
                def __init__(self, **data):
                    try:
                        super().__init__(**data)
                    except Exception as e:
                        raise ValueError(str(e))
                
                @classmethod
                def model_validate(cls, obj):
                    try:
                        return super().model_validate(obj)
                    except Exception as e:
                        raise ValueError(str(e))

            return ValidatedModel
            
        except Exception as e:
            raise ValueError(str(e))
