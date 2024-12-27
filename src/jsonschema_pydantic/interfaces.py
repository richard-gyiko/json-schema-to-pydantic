from abc import ABC, abstractmethod
from typing import Any, Type, Dict, List, Optional
from pydantic import BaseModel


class ITypeResolver(ABC):
    @abstractmethod
    def resolve_type(self, schema: Dict[str, Any], root_schema: Dict[str, Any]) -> Any:
        """Resolves JSON Schema types to Pydantic types"""
        pass


class IConstraintBuilder(ABC):
    @abstractmethod
    def build_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Builds Pydantic field constraints from JSON Schema"""
        pass


class ICombinerHandler(ABC):
    @abstractmethod
    def handle_all_of(
        self, schemas: List[Dict[str, Any]], root_schema: Dict[str, Any]
    ) -> Any:
        """Handles allOf combiner"""
        pass

    @abstractmethod
    def handle_any_of(
        self, schemas: List[Dict[str, Any]], root_schema: Dict[str, Any]
    ) -> Any:
        """Handles anyOf combiner"""
        pass

    @abstractmethod
    def handle_one_of(self, schema: Dict[str, Any], root_schema: Dict[str, Any]) -> Any:
        """Handles oneOf combiner"""
        pass


class IReferenceResolver(ABC):
    @abstractmethod
    def resolve_ref(
        self, ref: str, schema: Dict[str, Any], root_schema: Dict[str, Any]
    ) -> Any:
        """Resolves JSON Schema references"""
        pass


class IModelBuilder(ABC):
    @abstractmethod
    def create_pydantic_model(
        self, schema: Dict[str, Any], root_schema: Optional[Dict[str, Any]] = None
    ) -> Type[BaseModel]:
        """Creates a Pydantic model from JSON Schema"""
        pass