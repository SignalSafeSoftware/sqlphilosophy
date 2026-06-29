"""SQLAlchemy query helpers — ORM-first, Core for performance paths."""

from __future__ import annotations
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import date
from datetime import datetime
from typing import Any
from typing import cast
from typing import Mapping
from typing import TypeVar
from uuid import UUID
from sqlalchemy import and_
from sqlalchemy import bindparam
from sqlalchemy import delete
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import literal_column
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.sql import column
from sqlalchemy.sql import table
from sqlalchemy.sql.elements import BindParameter
from sqlphilosophy.audit.model import AuditMixin
from sqlphilosophy.sorting import OrderByMap
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.types import ApiObject
from sqlphilosophy.types import cursor_rowcount
from sqlphilosophy.types import JSONObject
from sqlphilosophy.types import JSONValue
from sqlphilosophy.types import PrimaryKey
from sqlphilosophy.types import RowMapping
from sqlphilosophy.types import RowValue
from sqlphilosophy.types import SqlFilter
from sqlphilosophy.types import SqlFilters
from sqlphilosophy.types import SqlOrderColumn
from sqlphilosophy.types import SqlTable

_ModelT = TypeVar("_ModelT", bound=DeclarativeBase)


def _mapped_model_class_for(value: object) -> type[DeclarativeBase] | None:
    candidate: object = value if isinstance(value, type) else value.__class__

    if not isinstance(candidate, type):
        return None

    try:
        sa_inspect(candidate)
    except NoInspectionAvailable:
        if not hasattr(candidate, "__mapper__"):
            return None

    return cast(type[DeclarativeBase], candidate)


def sql_table(table_name: str, *column_names: str) -> SqlTable:
    """Lightweight Core table — prefer ORM models unless you need Core performance."""
    return table(table_name, *[column(c) for c in column_names])


def get_column_value(entity: object) -> ApiObject:
    """Return mapped column values for an ORM entity instance."""
    instance_state = sa_inspect(entity, raiseerr=False)
    if instance_state is not None and hasattr(instance_state, "mapper"):
        mapper = instance_state.mapper
    else:
        from sqlphilosophy.sync.repository import BaseRepository

        model_cls = _mapped_model_class_for(entity)
        if model_cls is None:
            raise TypeError(f"{type(entity)!r} is not a mapped SQLAlchemy entity")
        try:
            insp = BaseRepository.inspect_model(model_cls)
        except Exception as exc:
            raise TypeError(f"{type(entity)!r} is not a mapped SQLAlchemy entity") from exc
        if not hasattr(insp, "mapper"):
            raise TypeError(f"{type(entity)!r} is not a mapped SQLAlchemy entity")
        mapper = insp.mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


def row_mapping(row: object) -> RowMapping:
    """Normalize a SQLAlchemy Row to a column-keyed dict."""
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        raw = dict(row._mapping)
    else:
        instance_state = sa_inspect(row, raiseerr=False)
        if instance_state is not None and hasattr(instance_state, "mapper"):
            return cast(RowMapping, get_column_value(row))
        raw = dict(cast(Mapping[str, RowValue], row))
    out: ApiObject = {}
    for key, val in raw.items():
        if hasattr(val, "__mapper__"):
            out.update(get_column_value(val))
        elif hasattr(key, "key"):
            out[str(key.key)] = val
        else:
            out[str(key)] = val
    return cast(RowMapping, out)


def row_mapping_opt(row: object | None) -> RowMapping | None:
    if row is None:
        return None
    return row_mapping(row)


def row_int(row: RowMapping, key: str) -> int:
    val = row[key]
    if isinstance(val, bool):
        raise TypeError(f"expected int for {key!r}, got bool")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        return int(val)
    raise TypeError(f"expected int for {key!r}, got {type(val).__name__}")


def row_opt_int(row: RowMapping, key: str) -> int | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, bool):
        raise TypeError(f"expected int | None for {key!r}, got bool")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        return int(val)
    raise TypeError(f"expected int | None for {key!r}, got {type(val).__name__}")


def row_str(row: RowMapping, key: str) -> str:
    val = row[key]
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool, UUID, date, datetime)):
        return str(val)
    if isinstance(val, bytes):
        return val.decode()
    raise TypeError(f"expected str for {key!r}, got {type(val).__name__}")


def row_opt_str(row: RowMapping, key: str) -> str | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool, UUID, date, datetime)):
        return str(val)
    if isinstance(val, bytes):
        return val.decode()
    raise TypeError(f"expected str | None for {key!r}, got {type(val).__name__}")


def row_bool(row: RowMapping, key: str) -> bool:
    val = row[key]
    if isinstance(val, bool):
        return val
    raise TypeError(f"expected bool for {key!r}, got {type(val).__name__}")


def row_opt_bool(row: RowMapping, key: str) -> bool | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    raise TypeError(f"expected bool | None for {key!r}, got {type(val).__name__}")


def row_float(row: RowMapping, key: str) -> float:
    val = row[key]
    if isinstance(val, bool):
        raise TypeError(f"expected float for {key!r}, got bool")
    if isinstance(val, float):
        return val
    if isinstance(val, int):
        return float(val)
    raise TypeError(f"expected float for {key!r}, got {type(val).__name__}")


def row_opt_float(row: RowMapping, key: str) -> float | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, bool):
        raise TypeError(f"expected float | None for {key!r}, got bool")
    if isinstance(val, float):
        return val
    if isinstance(val, int):
        return float(val)
    raise TypeError(f"expected float | None for {key!r}, got {type(val).__name__}")


def api_int(obj: Mapping[str, RowValue], key: str, default: int = 0) -> int:
    val = obj.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return default
    return default


def api_float(obj: Mapping[str, RowValue], key: str, default: float = 0.0) -> float:
    val = obj.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, int):
        return float(val)
    if isinstance(val, float):
        return val
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return default
    return default


def row_json(row: RowMapping, key: str) -> JSONValue:
    val = row[key]
    if isinstance(val, bool) or isinstance(val, (str, int, float, type(None))):
        return cast(JSONValue, val)
    if isinstance(val, dict):
        if not all(isinstance(k, str) for k in val):
            raise TypeError(f"expected JSON object keys to be str for {key!r}")
        return cast(JSONValue, val)
    if isinstance(val, list):
        return cast(JSONValue, val)
    raise TypeError(f"expected JSON value for {key!r}, got {type(val).__name__}")


def row_json_object(row: RowMapping, key: str) -> JSONObject:
    val = row[key]
    if isinstance(val, dict):
        if not all(isinstance(k, str) for k in val):
            raise TypeError(f"expected JSON object keys to be str for {key!r}")
        return cast(JSONObject, val)
    raise TypeError(f"expected JSON object for {key!r}, got {type(val).__name__}")


def row_opt_json_object(row: RowMapping, key: str) -> JSONObject | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        if not all(isinstance(k, str) for k in val):
            raise TypeError(f"expected JSON object keys to be str for {key!r}")
        return cast(JSONObject, val)
    raise TypeError(f"expected JSON object | None for {key!r}, got {type(val).__name__}")


def row_uuid(row: RowMapping, key: str) -> UUID:
    val = row[key]
    if isinstance(val, UUID):
        return val
    if isinstance(val, str):
        return UUID(val)
    raise TypeError(f"expected UUID for {key!r}, got {type(val).__name__}")


def row_opt_uuid(row: RowMapping, key: str) -> UUID | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    if isinstance(val, str):
        return UUID(val)
    raise TypeError(f"expected UUID | None for {key!r}, got {type(val).__name__}")


def rows_mapping(rows: Iterable[object]) -> list[RowMapping]:
    return [row_mapping(r) for r in rows]


def apply_mappings_page(
    session: Session,
    stmt: Any,
    *,
    limit: int,
    offset: int,
    params: RowMapping | None = None,
) -> list[RowMapping]:
    """Execute ``stmt`` with limit/offset; return normalized row mappings."""
    if limit < 0:
        raise ValueError("limit must be >= 0")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    paged = stmt.limit(limit).offset(offset)
    mapped = session.execute(paged, params or {}).mappings()
    rows = mapped.all() if hasattr(mapped, "all") else mapped
    return rows_mapping(rows)


def get_sort_column(
    sort: SortConfig,
    order_by: OrderByMap | None = None,
) -> object:
    """Resolve the primary ORDER BY expression for ``sort`` and optional client ``order_by``."""
    return sort.order_expression(order_by)


def expanding_in_param(
    name: str,
    values: Sequence[PrimaryKey],
) -> tuple[object, dict[str, list[str]]]:
    """Return ``(bindparam(..., expanding=True), {name: [str(v), ...]})`` for ``IN`` clauses."""
    param: BindParameter[Any] = bindparam(name, expanding=True)
    return param, {name: [str(value) for value in values]}


def partial_update_model(
    session: Session,
    model: type[_ModelT],
    pk_value: PrimaryKey,
    fields: RowMapping,
    writable: frozenset[str],
    *,
    pk_attr: str = "id",
    touch_updated_on: bool = False,
    extra_values: RowMapping | None = None,
) -> int:
    """Partial UPDATE on an ORM mapped class; ``fields`` keys must pass ``writable``."""
    if issubclass(model, AuditMixin):
        audit_updates = {k: v for k, v in fields.items() if k in writable}
        if extra_values:
            audit_updates = {**audit_updates, **extra_values}
        if not audit_updates:
            return 0
        row = session.get(model, pk_value)
        if row is None:
            return 0
        for key, value in audit_updates.items():
            setattr(row, key, value)
        session.flush()
        return 1
    core_updates: RowMapping = {k: v for k, v in fields.items() if k in writable}
    if extra_values:
        core_updates = {**core_updates, **extra_values}
    if not core_updates:
        return 0
    if touch_updated_on:
        core_updates = cast(
            RowMapping, {**dict(core_updates), "updated_on": cast(RowValue, func.now())}
        )
    pk_col = getattr(model, pk_attr)
    stmt = update(model).where(pk_col == pk_value).values(**core_updates)
    result = session.execute(stmt)
    return cursor_rowcount(result)


def partial_update(
    session: Session,
    table_name: str,
    pk_value: PrimaryKey,
    fields: RowMapping,
    writable: frozenset[str],
    *,
    pk_column: str = "id",
    touch_updated_on: bool = False,
    extra_values: RowMapping | None = None,
) -> int:
    """Core partial UPDATE — use ``partial_update_model`` when an ORM class exists."""
    updates: RowMapping = {k: v for k, v in fields.items() if k in writable}
    if extra_values:
        updates = {**updates, **extra_values}
    if not updates:
        return 0
    if touch_updated_on:
        updates = cast(RowMapping, {**dict(updates), "updated_on": cast(RowValue, func.now())})
    col_names = [pk_column, *updates.keys()]
    tbl = sql_table(table_name, *col_names)
    stmt = update(tbl).where(tbl.c[pk_column] == pk_value).values(**updates)
    result = session.execute(stmt)
    return cursor_rowcount(result)


def apply_writable_update(
    session: Session,
    model: type[DeclarativeBase],
    pk_value: PrimaryKey,
    values: RowMapping,
    writable: frozenset[str],
    *,
    pk_attr: str = "id",
) -> None:
    """Apply only ``writable`` keys from ``values`` to a single row; no-op when empty."""
    filtered = {k: v for k, v in values.items() if k in writable}
    if not filtered:
        return
    pk_col = getattr(model, pk_attr)
    session.execute(update(model).where(pk_col == pk_value).values(**filtered))


def delete_by_ids(
    session: Session,
    table_name: str,
    ids: list[object],
    *,
    pk_column: str = "id",
) -> int:
    if not ids:
        return 0
    tbl = sql_table(table_name, pk_column)
    stmt = delete(tbl).where(tbl.c[pk_column].in_(ids))
    result = session.execute(stmt)
    return cursor_rowcount(result)


def delete_by_ids_model(
    session: Session,
    model: type[_ModelT],
    ids: list[object],
    *,
    pk_attr: str = "id",
) -> int:
    if not ids:
        return 0
    pk_col = getattr(model, pk_attr)
    stmt = delete(model).where(pk_col.in_(ids))
    result = session.execute(stmt)
    return cursor_rowcount(result)


def col_eq(col_sql: str, param_name: str, value: object) -> tuple[SqlFilter, ApiObject]:
    return literal_column(col_sql) == bindparam(param_name), cast(
        ApiObject, {param_name: cast(RowValue, value)}
    )


def col_icontains(
    col_sql: str,
    param_name: str,
    raw: object,
) -> tuple[SqlFilter, ApiObject] | None:
    text_value = str(raw).strip()
    if not text_value:
        return None
    crit = func.lower(literal_column(col_sql)).like(bindparam(param_name))
    return crit, {param_name: f"%{text_value.lower()}%"}


def col_range(
    col_sql: str,
    param_name: str,
    operator: str,
    value: object,
) -> tuple[SqlFilter, ApiObject]:
    col: SqlOrderColumn = literal_column(col_sql)
    if operator == ">=":
        return col >= bindparam(param_name), cast(ApiObject, {param_name: cast(RowValue, value)})
    if operator == "<=":
        return col <= bindparam(param_name), cast(ApiObject, {param_name: cast(RowValue, value)})
    raise ValueError(f"unsupported operator: {operator}")


def merge_criteria(
    *parts: tuple[SqlFilters, ApiObject] | None,
) -> tuple[SqlFilters, ApiObject]:
    criteria: SqlFilters = []
    params: ApiObject = {}
    for part in parts:
        if part is None:
            continue
        crits, p = part
        criteria.extend(crits)
        params.update(p)
    return criteria, params


def combine_and(*criteria: SqlFilter | None) -> SqlFilter | None:
    present = [c for c in criteria if c is not None]
    if not present:
        return None
    return and_(*present)


def order_by_allowlist(
    order_key: str,
    ordering_map: Mapping[str, str],
    *,
    allowlist: frozenset[str],
) -> SqlOrderColumn:
    if order_key not in allowlist:
        raise ValueError(f"invalid order key: {order_key}")
    return literal_order_expr(ordering_map[order_key])


def literal_order_expr(spec: str) -> SqlOrderColumn:
    """Build ORDER BY from a SQL fragment such as ``a.started_at DESC``."""
    parts = spec.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].upper() == "DESC":
        return desc(literal_column(parts[0]))
    return literal_column(spec)


def order_expr_from_sort(
    column: str,
    direction: str,
    *,
    columns: Mapping[str, Mapping[str, str]],
) -> SqlOrderColumn:
    """Build an ORDER BY expression from ``(column, asc|desc)`` and a column spec map."""
    return literal_order_expr(columns[column][direction])


def count_from_subquery(session: Session, subq: Any) -> int:
    """Count rows from a subquery (path C helper for aggregate count wrappers)."""
    return int(session.execute(select(func.count()).select_from(subq)).scalar_one() or 0)


def count_from_table(
    session: Session,
    tbl: SqlTable,
    criteria: SqlFilters,
    params: RowMapping,
) -> int:
    stmt = select(func.count()).select_from(tbl)
    combined = combine_and(*criteria)
    if combined is not None:
        stmt = stmt.where(combined)
    return int(session.execute(stmt, params).scalar_one())


def select_page_from_table(
    session: Session,
    tbl: SqlTable,
    criteria: SqlFilters,
    params: RowMapping,
    *,
    order_by: SqlOrderColumn,
    limit: int,
    offset: int,
) -> list[object]:
    stmt = select(tbl)
    combined = combine_and(*criteria)
    if combined is not None:
        stmt = stmt.where(combined)
    stmt = stmt.order_by(order_by).limit(limit).offset(offset)
    return list(session.execute(stmt, params).mappings().all())
