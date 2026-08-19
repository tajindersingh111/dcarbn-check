from __future__ import annotations

import enum
import sqlalchemy.types as types

# Global monkeypatch to ensure SQLAlchemy native Enums map to their string values
# (e.g. 'active') instead of their member names (e.g. 'ACTIVE') when running on
# strict databases like PostgreSQL. This fixes a cross-compatibility issue
# between SQLite and PostgreSQL native Enum validation.
original_enum_init = types.Enum.__init__


def _patched_enum_init(self, *enums, **kw):
    if enums and isinstance(enums[0], type) and issubclass(enums[0], enum.Enum) and "values_callable" not in kw:
        kw["values_callable"] = lambda x: [e.value for e in x]
    original_enum_init(self, *enums, **kw)


types.Enum.__init__ = _patched_enum_init
