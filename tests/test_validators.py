import pytest
from autogen_mcp_tool_adapter.validators import SchemaValidator
from autogen_mcp_tool_adapter.exceptions import ValidationError

def test_basic_schema_validation():
    validator = SchemaValidator()
    
    # Valid schema
    validator.validate_schema({
        "type": "object",
        "properties": {"name": {"type": "string"}}
    })
    
    # Invalid type
    with pytest.raises(ValidationError):
        validator.validate_schema({"type": "invalid"})

def test_array_validation():
    validator = SchemaValidator()
    
    # Missing items
    with pytest.raises(ValidationError):
        validator.validate_schema({
            "type": "array"
        })
    
    # Invalid minItems type
    with pytest.raises(ValidationError):
        validator.validate_schema({
            "type": "array",
            "items": {"type": "string"},
            "minItems": "1"  # should be integer
        })

def test_object_validation():
    validator = SchemaValidator()
    
    # Required field not in properties
    with pytest.raises(ValidationError):
        validator.validate_schema({
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["age"]
        })
