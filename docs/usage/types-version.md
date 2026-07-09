# Version and typing aliases

[← Repository guide](../repository-guide.md)

---

## Package version

```python
import sqlphilosophy

print(sqlphilosophy.__version__)  # only public root export
```

## Explicit submodule imports

```python
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery, SortConfig
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.trusted_sql import col_eq, sql_table
from sqlphilosophy.types import PrimaryKey, RowMapping, SqlBindParams, SqlFilter, cursor_rowcount
```

## Common typing aliases (`sqlphilosophy.types`)

| Alias | Use |
|-------|-----|
| `PrimaryKey` | Repository PK arguments (`int \| str \| UUID`) |
| `IdList` | Lists of PKs for bulk delete |
| `RowMapping` | Dict-like result rows |
| `RowValue` | Bind-compatible values |
| `SqlFilter` | WHERE criteria (`ColumnElement[bool]`) |
| `SqlBindParams` | Execute bind dicts |
| `SqlSelect` | Typed SELECT aliases |
| `cursor_rowcount(result)` | DML rowcount after `session.execute` |

```python
from sqlalchemy import update
from sqlalchemy.orm import Session

from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.types import PrimaryKey, SqlBindParams, SqlFilter, cursor_rowcount


def archive_user(user_id: PrimaryKey, session: Session) -> int:
    repo = BaseRepository(User, session)
    criteria: list[SqlFilter] = [User.id == user_id]
    params: SqlBindParams = {}
    result = session.execute(update(User).where(*criteria).values(is_active=False), params)
    return cursor_rowcount(result)
```

See [feature-matrix.md](../feature-matrix.md) for the full alias list.

**Next:** [setup.md](./setup.md) · [feature-matrix.md](../feature-matrix.md)
