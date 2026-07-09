# Security Policy

## Supported versions

Python 3.12 and 3.13 (see `pyproject.toml` `requires-python`). Only the latest published release line receives security fixes.

## Reporting a vulnerability

Please report suspected security vulnerabilities **privately**. Do **not** open a public GitHub issue for security reports.

Email: security@signalsafe.software

Include a description, reproduction steps, affected versions, and impact if known. We aim to acknowledge reports within five business days.


## Security boundaries

This package helps application developers build SQLAlchemy repositories. It is **not** an ORM security sandbox.

### SQL and identifier trust

The following must be **developer-defined** and must **never** be built from end-user input:

- Raw SQL fragments passed to SQL helper functions
- Literal column names and table names
- Literal `ORDER BY` expressions
- Sort field allowlists and pagination keys wired into query builders

**User-supplied values must use bind parameters** (SQLAlchemy parameters / bound values), not string concatenation into SQL text or identifiers.

Import fragment helpers from **`sqlphilosophy.trusted_sql`** (canonical). The same names remain re-exported from `sqlphilosophy.sql` for backward compatibility:

```python
from sqlphilosophy.trusted_sql import col_eq, literal_order_expr, sql_table
```

### Other responsibilities

- Transaction boundaries and commit/rollback ownership remain with the application.
- Destructive helpers (for example truncate/delete utilities) assume the caller has already authorized the operation.
- Audit listeners record changes; they do not enforce access control.
