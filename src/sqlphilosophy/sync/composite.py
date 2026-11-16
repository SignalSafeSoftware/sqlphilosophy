"""Explicit composite-key CRUD using a caller-owned session and repository scope."""

from collections.abc import Sequence

from servicephilosophy import ServiceRepository
from sqlalchemy import delete, inspect, update
from sqlalchemy.orm import DeclarativeBase, Session

from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.types import PrimaryKey, RowMapping, SqlFilter, cursor_rowcount

type CompositeKey = tuple[PrimaryKey, ...]


class CompositeRepository[T: DeclarativeBase](ServiceRepository[RepositoryFactory]):
    """A separate opt-in contract; scalar-key repositories retain their API."""

    def __init__(self, model: type[T], session: Session, factory: RepositoryFactory | None = None) -> None:
        super().__init__(factory)
        self.model, self._session = model, session
        self.columns = tuple(inspect(model).primary_key)
        if len(self.columns) < 2:
            raise ValueError("Composite repositories require multiple primary-key columns")

    @property
    def session(self) -> Session:
        return self._session

    def criteria(self, identity: CompositeKey) -> tuple[SqlFilter, ...]:
        if not isinstance(identity, tuple) or len(identity) != len(self.columns):
            raise ValueError("Composite identity must supply every primary-key component")
        for column, value in zip(self.columns, identity, strict=True):
            if type(value) is not column.type.python_type:
                raise ValueError("Composite identity component has the wrong type")
        return tuple(column == value for column, value in zip(self.columns, identity, strict=True))

    def statement(self) -> StatementQueryBuilder[T]:
        factory = self.maybe_factory
        if factory is not None:
            return factory.create_statement(self.model)
        return SqlAlchemyStatementBuilder(self.session, self.model)

    def apply_scope(self, statement: StatementQueryBuilder[T]) -> StatementQueryBuilder[T]:
        return statement

    def find_entity(self, *, criteria: Sequence[SqlFilter], lock: bool = False) -> T | None:
        if not criteria:
            raise ValueError("Composite lookups require explicit criteria")
        statement = self.apply_scope(self.statement()).where(*criteria)
        if lock:
            statement = statement.with_for_update()
        return statement.scalars().first()

    def add(self, row: T) -> T:
        self.session.add(row)
        self.session.flush()
        return row

    def update_partial(self, identity: CompositeKey, fields: RowMapping, writable: frozenset[str]) -> int:
        primary = {inspect(self.model).get_property_by_column(column).key for column in self.columns}
        columns = set(inspect(self.model).column_attrs.keys())
        if not writable or not writable <= columns or writable & primary or not fields.keys() <= writable:
            raise ValueError("Composite updates require a mapped non-identity writable allowlist")
        criteria = self.criteria(identity)
        if not fields:
            return 0
        result = self.session.execute(update(self.model).where(*criteria).values(**fields))
        return cursor_rowcount(result)

    def remove(self, identity: CompositeKey) -> bool:
        result = self.session.execute(delete(self.model).where(*self.criteria(identity)))
        return cursor_rowcount(result) > 0
