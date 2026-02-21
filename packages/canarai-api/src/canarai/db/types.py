"""Custom SQLAlchemy column types."""

import json

from sqlalchemy import Text, TypeDecorator


class JSONType(TypeDecorator):
    """Platform-agnostic JSON column type.

    Uses native JSON on PostgreSQL, stores as TEXT with json
    serialization on SQLite.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None
