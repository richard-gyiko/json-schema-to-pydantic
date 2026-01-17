from pydantic import RootModel, ValidationError
import pytest
from json_schema_to_pydantic.model_builder import PydanticModelBuilder


def test_string_root_model():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "customers key",
        "type": "string",
    }

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    assert issubclass(model, RootModel)
    assert model.model_validate("test").root == "test"
    with pytest.raises(ValidationError):
        model.model_validate(123)


def test_integer_root_model():
    schema = {"title": "age", "type": "integer", "minimum": 0}

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    assert issubclass(model, RootModel)
    assert model.model_validate(10).root == 10
    with pytest.raises(ValidationError):
        model.model_validate("test")
    with pytest.raises(ValidationError):
        model.model_validate(-1)


def test_enum_root_model():
    schema = {"title": "status", "enum": ["active", "inactive"]}

    builder = PydanticModelBuilder()
    model = builder.create_pydantic_model(schema)

    assert issubclass(model, RootModel)
    assert model.model_validate("active").root == "active"
    with pytest.raises(ValidationError):
        model.model_validate("pending")
