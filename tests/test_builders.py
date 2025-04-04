from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyUrl

from json_schema_to_pydantic.builders import ConstraintBuilder


def test_string_constraints():
    builder = ConstraintBuilder()

    constraints = builder.build_constraints(
        {"minLength": 3, "maxLength": 10, "pattern": "^[A-Z].*$"}
    )

    assert constraints["min_length"] == 3
    assert constraints["max_length"] == 10
    assert constraints["pattern"] == "^[A-Z].*$"


def test_format_constraints():
    builder = ConstraintBuilder()

    email_constraints = builder.build_constraints({"format": "email"})
    assert isinstance(email_constraints, dict)
    assert "pattern" in email_constraints
    assert (
        email_constraints["pattern"]
        == r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    assert builder.build_constraints({"format": "date-time"}) == datetime
    assert builder.build_constraints({"format": "uuid"}) == UUID


def test_numeric_constraints():
    builder = ConstraintBuilder()

    constraints = builder.build_constraints(
        {"minimum": 0, "maximum": 100, "multipleOf": 5}
    )

    assert constraints["ge"] == 0
    assert constraints["le"] == 100
    assert constraints["multiple_of"] == 5


def test_array_constraints():
    """Test array-specific constraints."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints({"minItems": 1, "maxItems": 5})

    assert constraints["min_length"] == 1
    assert constraints["max_length"] == 5


def test_exclusive_numeric_constraints():
    """Test exclusive minimum/maximum constraints."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints(
        {"exclusiveMinimum": 0, "exclusiveMaximum": 100}
    )

    assert constraints["gt"] == 0
    assert constraints["lt"] == 100


def test_multiple_constraints():
    """Test combining multiple types of constraints."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints(
        {"minLength": 3, "maxLength": 10, "pattern": "^[A-Z].*$", "format": "email"}
    )

    assert "pattern" in constraints
    assert constraints["pattern"] == r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    assert constraints["min_length"] == 3
    assert constraints["max_length"] == 10


def test_empty_schema():
    """Test handling of empty schema."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints({})

    assert constraints == {}


def test_const_constraint():
    """Test handling of const constraint."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints({"const": "dog"})

    assert constraints == Literal["dog"]


def test_uri_format():
    """Test URI format handling."""
    builder = ConstraintBuilder()

    constraints = builder.build_constraints({"format": "uri"})

    assert constraints == AnyUrl


def test_merge_numeric_constraints():
    """Test merging numeric constraints."""
    builder = ConstraintBuilder()

    schema1 = {"minimum": 0, "maximum": 100}
    schema2 = {"minimum": 10, "maximum": 50}

    merged = builder.merge_constraints(schema1, schema2)
    assert merged["minimum"] == 10  # Takes the more restrictive minimum
    assert merged["maximum"] == 50  # Takes the more restrictive maximum


def test_merge_string_constraints():
    """Test merging string constraints."""
    builder = ConstraintBuilder()

    schema1 = {"minLength": 3, "maxLength": 10, "pattern": "^[A-Z]"}
    schema2 = {"minLength": 5, "maxLength": 8, "pattern": "[0-9]$"}

    merged = builder.merge_constraints(schema1, schema2)
    assert merged["minLength"] == 5
    assert merged["maxLength"] == 8
    assert "(?=^[A-Z])(?=[0-9]$)" in merged["pattern"]


def test_merge_mixed_constraints():
    """Test merging mixed constraint types."""
    builder = ConstraintBuilder()

    schema1 = {"minimum": 0, "minLength": 3}
    schema2 = {"maximum": 100, "maxLength": 10}

    merged = builder.merge_constraints(schema1, schema2)
    assert merged["minimum"] == 0
    assert merged["maximum"] == 100
    assert merged["minLength"] == 3
    assert merged["maxLength"] == 10


def test_merge_with_empty_schema():
    """Test merging with an empty schema."""
    builder = ConstraintBuilder()

    schema1 = {"minimum": 0}
    schema2 = {}

    merged = builder.merge_constraints(schema1, schema2)
    assert merged["minimum"] == 0
