import pytest
from autogen_mcp_tool_adapter.schema_builder import JsonSchemaToPydantic

def test_basic_types():
    schema = {
        "type": "object",
        "properties": {
            "string_field": {"type": "string"},
            "integer_field": {"type": "integer"},
            "number_field": {"type": "number"},
            "boolean_field": {"type": "boolean"}
        }
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "BasicTypes")
    
    # All fields should be optional by default
    instance = Model()
    assert instance.string_field is None
    assert instance.integer_field is None
    assert instance.number_field is None
    assert instance.boolean_field is None

def test_required_fields():
    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"}
        },
        "required": ["required_field"]
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "RequiredFields")
    
    # Should raise validation error for missing required field
    with pytest.raises(ValueError):
        Model()
    
    # Should work with required field
    instance = Model(required_field="test", optional_field=None)
    assert instance.required_field == "test"
    assert instance.optional_field is None

def test_nested_objects():
    schema = {
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"}
                }
            }
        }
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "NestedObject")
    
    instance = Model(nested={"field": "test"})
    assert instance.nested.field == "test"

def test_array_types():
    schema = {
        "type": "object",
        "properties": {
            "string_array": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "ArrayTypes")
    
    instance = Model(string_array=["test1", "test2"])
    assert instance.string_array == ["test1", "test2"]

def test_validation_constraints():
    schema = {
        "type": "object",
        "properties": {
            "limited_string": {
                "type": "string",
                "minLength": 2,
                "maxLength": 5
            },
            "limited_number": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100
            }
        }
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "Validation")
    
    # Should raise for too short string
    with pytest.raises(ValueError):
        Model(limited_string="a")
    
    # Should raise for too large number
    with pytest.raises(ValueError):
        Model(limited_number=101)
    
    # Should work with valid values
    instance = Model(limited_string="test", limited_number=50)
    assert instance.limited_string == "test"
    assert instance.limited_number == 50

def test_complex_schema():
    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100
            },
            "age": {
                "type": "integer",
                "minimum": 0
            },
            "addresses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"}
                    },
                    "required": ["street", "city"]
                }
            }
        },
        "required": ["name"]
    }
    
    builder = JsonSchemaToPydantic()
    Model = builder.convert_schema_to_model(schema, "ComplexModel")
    
    instance = Model(
        name="John Doe",
        age=30,
        addresses=[
            {"street": "123 Main St", "city": "Boston"},
            {"street": "456 Side St", "city": "New York"}
        ]
    )
    
    assert instance.name == "John Doe"
    assert instance.age == 30
    assert len(instance.addresses) == 2
    assert instance.addresses[0].street == "123 Main St"
    assert instance.addresses[1].city == "New York"
