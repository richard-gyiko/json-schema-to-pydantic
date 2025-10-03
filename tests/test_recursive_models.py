"""Tests for recursive model handling."""
from json_schema_to_pydantic.model_builder import PydanticModelBuilder


def test_recursive_model_with_array():
    """Test creation of recursive models where objects reference themselves through arrays."""
    builder = PydanticModelBuilder()
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Node": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string"
                    },
                    "children": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/Node"
                        }
                    }
                },
                "required": ["value"]
            }
        },
        "type": "object",
        "properties": {
            "root": {
                "$ref": "#/definitions/Node"
            }
        },
        "required": ["root"]
    }

    # Should not raise RecursionError
    model = builder.create_pydantic_model(schema)
    
    # Verify model was created
    assert model is not None
    assert "root" in model.model_fields
    
    # Test instantiation with nested structure
    instance = model(root={
        "value": "root",
        "children": [
            {"value": "child1", "children": [{"value": "grandchild1"}]},
            {"value": "child2"}
        ]
    })
    
    # Verify the structure
    assert instance.root.value == "root"
    assert len(instance.root.children) == 2
    assert instance.root.children[0].value == "child1"
    assert len(instance.root.children[0].children) == 1
    assert instance.root.children[0].children[0].value == "grandchild1"
    assert instance.root.children[1].value == "child2"
    assert instance.root.children[1].children is None


def test_recursive_model_with_optional_reference():
    """Test recursive models with optional self-reference."""
    builder = PydanticModelBuilder()
    schema = {
        "definitions": {
            "LinkedNode": {
                "type": "object",
                "properties": {
                    "data": {"type": "string"},
                    "next": {"$ref": "#/definitions/LinkedNode"}
                },
                "required": ["data"]
            }
        },
        "type": "object",
        "properties": {
            "head": {"$ref": "#/definitions/LinkedNode"}
        },
        "required": ["head"]
    }

    model = builder.create_pydantic_model(schema)
    
    # Test with a linked list
    instance = model(head={
        "data": "first",
        "next": {
            "data": "second",
            "next": {
                "data": "third"
            }
        }
    })
    
    assert instance.head.data == "first"
    assert instance.head.next.data == "second"
    assert instance.head.next.next.data == "third"
    assert instance.head.next.next.next is None


def test_recursive_model_title_from_definition():
    """Test that recursive models get their title from the definition name."""
    builder = PydanticModelBuilder()
    schema = {
        "definitions": {
            "TreeNode": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer"},
                    "left": {"$ref": "#/definitions/TreeNode"},
                    "right": {"$ref": "#/definitions/TreeNode"}
                },
                "required": ["value"]
            }
        },
        "$ref": "#/definitions/TreeNode"
    }

    model = builder.create_pydantic_model(schema)
    
    # The model should be named TreeNode, not DynamicModel
    assert model.__name__ == "TreeNode"
    
    # Test a binary tree structure
    instance = model(
        value=1,
        left={"value": 2, "left": {"value": 4}},
        right={"value": 3}
    )
    
    assert instance.value == 1
    assert instance.left.value == 2
    assert instance.left.left.value == 4
    assert instance.right.value == 3


def test_multiple_recursive_definitions():
    """Test schema with multiple mutually recursive definitions."""
    builder = PydanticModelBuilder()
    schema = {
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Person"}
                    },
                    "spouse": {"$ref": "#/definitions/Person"}
                },
                "required": ["name"]
            }
        },
        "$ref": "#/definitions/Person"
    }

    model = builder.create_pydantic_model(schema)
    
    # Test a family tree
    instance = model(
        name="Alice",
        children=[
            {"name": "Bob"},
            {"name": "Carol"}
        ],
        spouse={"name": "David"}
    )
    
    assert instance.name == "Alice"
    assert len(instance.children) == 2
    assert instance.children[0].name == "Bob"
    assert instance.spouse.name == "David"
