from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel


class ITypeResolver(ABC):
    @abstractmethod
    def resolve_type(self, schema: dict, root_schema: dict) -> Any:
        """Resolves JSON Schema types to Pydantic types"""
        pass


class IConstraintBuilder(ABC):
    @abstractmethod
    def build_constraints(self, schema: dict) -> dict:
        """Builds Pydantic field constraints from JSON Schema"""
        pass


class ICombinerHandler(ABC):
    @abstractmethod
    def handle_all_of(self, schemas: list, root_schema: dict) -> Any:
        """Handles allOf combiner"""
        pass

    @abstractmethod
    def handle_any_of(self, schemas: list, root_schema: dict) -> Any:
        """Handles anyOf combiner"""
        pass

    @abstractmethod
    def handle_one_of(self, schema: dict, root_schema: dict) -> Any:
        """Handles oneOf combiner"""
        pass


class IReferenceResolver(ABC):
    @abstractmethod
    def resolve_ref(self, ref: str, schema: dict, root_schema: dict) -> Any:
        """Resolves JSON Schema references"""
        pass


class IModelBuilder(ABC):
    @abstractmethod
    def create_pydantic_model(
        self, schema: dict, root_schema: dict = None
    ) -> Type[BaseModel]:
        """Creates a Pydantic model from JSON Schema"""
        pass
