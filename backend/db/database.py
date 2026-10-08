"""Database access stub — MongoDB edition.

The original SQLAlchemy engine/session has been replaced with Motor (async MongoDB).
Use `backend.core.db.get_db()` for direct MongoDB access.

This module is preserved for backward compatibility with imports that may reference it.
"""

from backend.core.db import get_db

# Alias for any code that imports get_db from here
__all__ = ["get_db"]
