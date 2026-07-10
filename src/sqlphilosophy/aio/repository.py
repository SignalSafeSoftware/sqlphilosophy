"""Generic async session-bound repository for ORM CRUD."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from servicephilosophy import ServiceRepository
from sqlalchemy import delete, func, select, update
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.interfaces import LoaderOption

from sqlphilosophy._repository_shared import (
    bulk_update_allowed,
    criteria_delete_allowed,
    extract_primary_keys,
    lookup_not_found_message,
    plan_partial_update,
    require_batch_size,
    require_mappings_page_limits,
    require_page_and_limit,
    require_single_column_primary_key,
)
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder, AsyncStatementQueryBuilder
from sqlphilosophy.sorting import ListQuery, SortConfig
from sqlphilosophy.sql import rows_mapping
from sqlphilosophy.types import (
    IdList,
    PrimaryKey,
    RowMapping,
    RowValue,
    SqlBindParams,
    SqlFilter,
    SqlSelect,
    cursor_rowcount,
)

LoadRelations = Sequence[LoaderOption]


class AsyncBaseRepository[T: DeclarativeBase, U: AsyncRepositoryFactory](ServiceRepository[U]):
    """Async session-scoped CRUD helpers for a single mapped model."""

    def __init__(
        self,
        model: type[T],
        session: AsyncSession,
        factory: U | None = None,
    ) -> None:
        super().__init__(factory)
        self.model = model
        self._session = session
        self._pk_column = require_single_column_primary_key(model, self.inspect_model(model))

    @classmethod
    def inspect_model(cls, model: type[DeclarativeBase]) -> Any:
        """Return SQLAlchemy ORM mapper inspection for ``model``."""
        return sa_inspect(model)

    def inspect(self) -> Any:
        """Return SQLAlchemy ORM mapper inspection for this repository's model."""
        return self.inspect_model(self.model)

    async def list_table_names(self) -> frozenset[str]:
        """Return visible table names on the session connection."""
        connection = await self._session.connection()

        def _names(sync_conn: object) -> frozenset[str]:
            insp = sa_inspect(sync_conn)
            if insp is None:
                return frozenset()
            return frozenset(insp.get_table_names())

        return await connection.run_sync(_names)

    async def has_table(self, table_name: str) -> bool:
        """True when ``table_name`` exists on the session connection."""
        return table_name in await self.list_table_names()

    def _apply_load_relations(self, stmt: Any, load_relations: LoadRelations | None) -> Any:
        if load_relations:
            return stmt.options(*load_relations)
        return stmt

    async def _scalar_result(self, stmt: Any, *, unique: bool = False) -> Any:
        result = await self._session.scalars(stmt)
        if unique:
            return result.unique()
        return result

    async def fetch_statement_mappings(self, stmt: Any, params: RowMapping | None = None) -> list[RowMapping]:
        """Execute ``stmt`` and return all rows as mappings."""
        result = await self._session.execute(stmt, params or {})
        mapped = result.mappings()
        rows = mapped.all() if hasattr(mapped, "all") else mapped
        return rows_mapping(rows)

    async def scalar_count(self, stmt: SqlSelect, params: SqlBindParams | None = None) -> int:
        """Execute a scalar count/select statement and return ``int``."""
        result = await self._session.execute(stmt, params or {})
        return int(result.scalar_one())

    async def iter_mappings(self, stmt: SqlSelect, params: SqlBindParams | None = None):
        """Yield each result row as a plain ``dict``."""
        result = await self._session.execute(stmt, params or {})
        for row in result.mappings():
            yield dict(row)

    async def fetch_mapping_first(self, stmt: SqlSelect, params: SqlBindParams | None = None) -> RowMapping | None:
        """Execute ``stmt`` and return the first row as a mapping, or ``None``."""
        result = await self._session.execute(stmt, params or {})
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def fetch_mapping_one(self, stmt: SqlSelect, params: SqlBindParams | None = None) -> RowMapping:
        """Execute ``stmt`` and return exactly one row as a mapping."""
        result = await self._session.execute(stmt, params or {})
        return dict(result.mappings().one())

    async def fetch_mappings_page(
        self,
        stmt: Any,
        *,
        limit: int,
        offset: int,
        params: RowMapping | None = None,
    ) -> list[RowMapping]:
        """Execute ``stmt`` with limit/offset; return normalized row mappings."""
        require_mappings_page_limits(limit=limit, offset=offset)
        paged = stmt.limit(limit).offset(offset)
        return await self.fetch_statement_mappings(paged, params)

    async def fetch_sorted_mappings(
        self,
        stmt: Any,
        *,
        list_query: ListQuery,
        params: RowMapping | None = None,
        sort: SortConfig | None = None,
    ) -> list[RowMapping]:
        """Apply optional sort, then return one page of row mappings."""
        if sort is not None:
            stmt = stmt.order_by(*sort.order_clauses(list_query.order_by))
        return await self.fetch_mappings_page(
            stmt,
            limit=list_query.limit,
            offset=list_query.offset,
            params=params,
        )

    async def get_by_id(self, obj_id: PrimaryKey, load_relations: LoadRelations | None = None) -> T | None:
        """Fetch a single record by primary key with optional eager loading."""
        stmt = select(self.model).where(self._pk_column == obj_id)
        stmt = self._apply_load_relations(stmt, load_relations)
        result = await self._session.scalars(stmt)
        return result.first()

    async def exists(self, obj_id: PrimaryKey) -> bool:
        """True when a row exists for the primary key."""
        return await self.get_by_id(obj_id) is not None

    async def exists_where(self, **filters: RowValue) -> bool:
        """True when at least one row matches optional equality filters."""
        return await self.count(**filters) > 0

    async def count(self, **filters: RowValue) -> int:
        """Count rows matching optional equality filters."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        result = await self._session.scalar(stmt)
        return int(result or 0)

    async def first(self, load_relations: LoadRelations | None = None, **filters: RowValue) -> T | None:
        """Return the first row matching filters, with optional eager loading."""
        stmt = select(self.model).filter_by(**filters).limit(1)
        stmt = self._apply_load_relations(stmt, load_relations)
        result = await self._session.scalars(stmt)
        return result.first()

    async def get(self, obj_id: PrimaryKey, load_relations: LoadRelations | None = None) -> T:
        """Fetch a single record by primary key; raise if missing."""
        obj = await self.get_by_id(obj_id, load_relations=load_relations)
        if obj is None:
            raise LookupError(lookup_not_found_message(self.model, obj_id))
        return obj

    async def get_many(self, ids: Sequence[PrimaryKey], load_relations: LoadRelations | None = None) -> Sequence[T]:
        """Fetch multiple records by primary key."""
        if not ids:
            return []
        stmt = select(self.model).where(self._pk_column.in_(ids))
        stmt = self._apply_load_relations(stmt, load_relations)
        result = await self._scalar_result(stmt, unique=load_relations is not None)
        return result.all()

    async def filter(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: LoadRelations | None = None,
        **filters: RowValue,
    ) -> Sequence[T]:
        """Return rows matching optional equality filters, optionally paginated."""
        require_page_and_limit(page=page, limit=limit)
        stmt = select(self.model).filter_by(**filters).order_by(self._pk_column)
        if limit is not None:
            stmt = stmt.limit(limit).offset((page - 1) * limit)
        stmt = self._apply_load_relations(stmt, load_relations)
        result = await self._scalar_result(stmt, unique=load_relations is not None)
        return result.all()

    async def get_all(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: LoadRelations | None = None,
    ) -> Sequence[T]:
        """Fetch records for this model type, optionally paginated by ``page`` and ``limit``."""
        require_page_and_limit(page=page, limit=limit)
        statement = select(self.model).order_by(self._pk_column)
        if limit is not None:
            statement = statement.limit(limit).offset((page - 1) * limit)
        statement = self._apply_load_relations(statement, load_relations)
        result = await self._scalar_result(statement, unique=load_relations is not None)
        return result.all()

    async def get_with_join(
        self,
        target_model: type[Any],
        *filter_expressions: Any,
        join_on: Any = None,
    ) -> Sequence[tuple[T, Any]]:
        """Explicit INNER JOIN returning ``(base_row, target_row)`` tuples."""
        stmt = select(self.model, target_model)
        if join_on is not None:  # noqa: SIM108
            stmt = stmt.join(target_model, join_on)
        else:
            stmt = stmt.join(target_model)  # pragma: no cover
        if filter_expressions:
            stmt = stmt.where(*filter_expressions)
        result = await self._session.execute(stmt)
        return cast(Sequence[tuple[T, Any]], result.all())

    async def create(self, **fields: object) -> T:
        """Construct, stage, and flush a new instance."""
        return await self.add(self.model(**fields))

    async def get_or_create(
        self,
        *,
        defaults: RowMapping | None = None,
        **lookup: RowValue,
    ) -> tuple[T, bool]:
        """Return ``(instance, created)`` for equality ``lookup`` filters."""
        existing = await self.first(load_relations=None, **lookup)
        if existing is not None:
            return existing, False
        payload: RowMapping = {**(defaults or {}), **lookup}
        return await self.create(**payload), True

    async def add(self, obj: T) -> T:
        """Stage a new instance; caller commits in the orchestration layer."""
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def update_partial(
        self,
        obj_id: PrimaryKey,
        fields: RowMapping,
        writable: frozenset[str],
        *,
        touch_updated_on: bool = False,
    ) -> int:
        """Apply a partial update; returns affected row count (0 if none)."""
        plan = plan_partial_update(
            self.model,
            fields,
            writable,
            touch_updated_on=touch_updated_on,
        )
        if plan.action == "skip":
            return 0
        if plan.action == "audit":
            row = await self._session.get(self.model, obj_id)
            if row is None:
                return 0
            updates = plan.updates_for("audit")
            for key, value in updates.items():
                setattr(row, key, value)
            await self._session.flush()
            return 1
        if plan.action == "core":
            updates = plan.updates_for("core")
            stmt = update(self.model).where(self._pk_column == obj_id).values(**updates)
            result = await self._session.execute(stmt)
            return cursor_rowcount(result)
        raise RuntimeError(f"unexpected partial update plan action: {plan.action!r}")

    async def update_where(
        self,
        *,
        criteria: Sequence[SqlFilter],
        values: RowMapping,
        params: SqlBindParams | None = None,
    ) -> int:
        """Bulk UPDATE rows matching ``criteria``; returns affected row count."""
        if not bulk_update_allowed(values):
            return 0
        stmt = update(self.model).where(*criteria).values(**values)
        result = await self._session.execute(stmt, params or {})
        return cursor_rowcount(result)

    async def delete_where(
        self,
        *,
        criteria: Sequence[SqlFilter],
        params: SqlBindParams | None = None,
    ) -> int:
        """Delete rows matching ``criteria`` via PK lookup + ``delete_many``."""
        if not criteria_delete_allowed(criteria):
            return 0
        pk_key = self._pk_column.key
        builder = self.statement().select_columns(self._pk_column).where(*criteria)
        if params:
            builder = builder.with_params(params)
        rows = await builder.mappings().all()
        ids = extract_primary_keys(rows, pk_key)
        return await self.delete_many(ids)

    async def remove(self, obj_id: PrimaryKey) -> bool:
        """Delete a record by primary key."""
        statement = delete(self.model).where(self._pk_column == obj_id)
        result = await self._session.execute(statement)
        return cursor_rowcount(result) > 0

    async def delete_many(self, ids: IdList) -> int:
        """Delete multiple records by primary key."""
        if not ids:
            return 0
        stmt = delete(self.model).where(self._pk_column.in_(ids))
        result = await self._session.execute(stmt)
        return cursor_rowcount(result)

    async def delete_all(self) -> int:
        """Delete every row for this model. Dev/ops only — prefer ``delete_where`` in app code."""
        result = await self._session.execute(delete(self.model))
        return cursor_rowcount(result)

    async def batched_purge_ids(
        self,
        *,
        criteria: list[SqlFilter],
        batch_size: int,
    ) -> int:
        """Delete rows matching ``criteria`` in ``batch_size`` chunks, committing each batch."""
        require_batch_size(batch_size)
        pk_key = self._pk_column.key
        total = 0
        while True:
            rows = await (
                self.statement().select_columns(self._pk_column).where(*criteria).limit(batch_size).mappings().all()
            )
            ids = extract_primary_keys(rows, pk_key)
            if not ids:
                break
            total += await self.delete_many(ids)
            await self._session.commit()
        return total

    def statement(self) -> AsyncStatementQueryBuilder[T]:
        """Return a fluent statement builder for reads on this model (default read path)."""
        factory = self.maybe_factory
        if factory is not None:
            return factory.create_statement(self.model)
        return AsyncSqlAlchemyStatementBuilder(self._session, self.model)

    def for_repo[R: AsyncBaseRepository[Any, Any]](self, repo_class: type[R]) -> R:
        """Return a typed entity repository sharing this session and factory.

        Raises ``FactoryRequiredError`` when no factory was configured.
        """
        return cast(R, self.factory.get_repository(repo_class))
