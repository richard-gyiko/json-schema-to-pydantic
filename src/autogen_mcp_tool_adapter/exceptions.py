class SchemaError(Exception):
    """Base class for schema-related errors"""

    pass


class ValidationError(SchemaError):
    """Invalid schema structure"""

    pass


class TypeError(SchemaError):
    """Invalid or unsupported type"""

    pass


class CombinerError(SchemaError):
    """Error in schema combiners"""

    pass


class ReferenceError(SchemaError):
    """Error in schema references"""

    pass
