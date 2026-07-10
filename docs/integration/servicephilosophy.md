# Integrating servicePhilosophy into sqlPhilosophy

Plan for adopting [`servicephilosophy`](https://github.com/SignalSafeSoftware/servicephilosophy) as the shared factory-aware base for sqlPhilosophy repositories.

**Status:** implemented.

---

## Goal

Move factory storage and access out of sqlPhilosophy’s repository classes and into the neutral `ServiceRepository[FactoryT]` base from servicePhilosophy. sqlPhilosophy keeps all SQLAlchemy, model, session, and CRUD behavior; servicePhilosophy only owns optional factory wiring.

---

## Current state

Sync and async repositories store the factory directly on the instance:

```python
# src/sqlphilosophy/sync/repository.py
class BaseRepository[T: DeclarativeBase, U: RepositoryFactory | None]:
    def __init__(
        self,
        model: type[T],
        session: Session,
        factory: RepositoryFactory | None = None,
    ) -> None:
        self.model = model
        self._session = session
        self._factory = factory
        ...
```

```python
# src/sqlphilosophy/aio/repository.py
class AsyncBaseRepository[T: DeclarativeBase, U: AsyncRepositoryFactory | None]:
    def __init__(
        self,
        model: type[T],
        session: AsyncSession,
        factory: AsyncRepositoryFactory | None = None,
    ) -> None:
        self.model = model
        self._session = session
        self._factory = factory
        ...
```

Factory checks are inlined where needed:

```python
# sync + async — statement()
if self._factory is not None:
    return self._factory.create_statement(self.model)
return SqlAlchemyStatementBuilder(self._session, self.model)  # or AsyncSqlAlchemyStatementBuilder

# sync + async — for_repo()
if self._factory is None:
    raise RuntimeError("for_repo() requires a RepositoryFactory")  # async: AsyncRepositoryFactory
return cast(R, self._factory.get_repository(repo_class))
```

Protocols mirror `_factory: U | None` on `BaseRepositoryProtocol` / `AsyncBaseRepositoryProtocol` in:

- `src/sqlphilosophy/sync/protocols.py`
- `src/sqlphilosophy/aio/protocols.py`

There is **no** runtime dependency on servicePhilosophy today (`pyproject.toml` depends only on SQLAlchemy).

---

## Target state

```python
from servicephilosophy import ServiceRepository

class BaseRepository[T: DeclarativeBase, U: RepositoryFactory](
    ServiceRepository[U],
):
    def __init__(
        self,
        model: type[T],
        session: Session,
        factory: U | None = None,
    ) -> None:
        super().__init__(factory)
        self.model = model
        self._session = session
        ...
```

```python
from servicephilosophy import ServiceRepository

class AsyncBaseRepository[T: DeclarativeBase, U: AsyncRepositoryFactory](
    ServiceRepository[U],
):
    def __init__(
        self,
        model: type[T],
        session: AsyncSession,
        factory: U | None = None,
    ) -> None:
        super().__init__(factory)
        self.model = model
        self._session = session
        ...
```

After inheritance, factory access uses the servicePhilosophy surface:

| Access | Behavior |
|--------|----------|
| `self.factory` | Returns `U`; raises `FactoryRequiredError` when missing |
| `self.maybe_factory` | Returns `U \| None` |
| `self.has_factory` | `True` when a factory was passed at construction |

Internal methods should prefer these properties over reading `_factory` directly ( `_factory` remains the backing store on `ServiceRepository` ).

### `statement()` and `for_repo()`

**`statement()`** — keep existing fallback when no factory is configured:

```python
def statement(self) -> StatementQueryBuilder[T]:
    if self.has_factory:
        return self.factory.create_statement(self.model)
    return SqlAlchemyStatementBuilder(self._session, self.model)
```

Use `self.has_factory` / `self.maybe_factory` rather than `self._factory is not None` so behavior stays explicit and typed.

**`for_repo()`** — require a factory via the shared error type:

```python
def for_repo[R: BaseRepository[Any, Any]](self, repo_class: type[R]) -> R:
    return cast(R, self.factory.get_repository(repo_class))
```

`self.factory` raises `FactoryRequiredError` when no factory was configured. Consider re-exporting `FactoryRequiredError` from `sqlphilosophy` for callers that catch factory-missing errors (optional follow-up).

Async `AsyncBaseRepository` follows the same pattern with `AsyncRepositoryFactory` and `AsyncStatementQueryBuilder`.

---

## Design rationale

### What `ServiceRepository[FactoryT]` provides

- Optional factory storage at construction
- `.factory`, `.maybe_factory`, and `.has_factory`
- No model, session, SQL, HTTP, or framework assumptions

### What `BaseRepository[ModelT, FactoryT]` still provides

- SQLAlchemy model binding (`model: type[ModelT]`)
- Session / async session binding (`_session`)
- CRUD helpers, query builders, sorting, trusted SQL, audit hooks
- **`statement()`** and **`for_repo()`** as SQL-specific conveniences

### Separation of concerns

```text
servicePhilosophy
  ServiceRepository[FactoryT]     ← factory wiring only

sqlPhilosophy
  BaseRepository[ModelT, FactoryT]
  AsyncBaseRepository[ModelT, FactoryT]   ← model + session + SQL CRUD

application
  UserRepository(BaseRepository[User, AppFactory])   ← domain methods
```

- **`ServiceRepository` is not a SQL repository.** It does not know about models or sessions.
- **`BaseRepository` is not a replacement for `ServiceRepository`.** It extends it with SQL/model behavior.
- **SQL repositories still require a model.** Application subclasses must still pass `model` and `session`.
- **`ServiceRepository` itself does not require a model.** Business-only services can use it without sqlPhilosophy.
- **Existing SQL CRUD behavior should remain unchanged.** This is an inheritance and accessor refactor, not a query-semantics change.

### Protocol alignment

`BaseRepositoryProtocol` / `AsyncBaseRepositoryProtocol` should expose the same factory surface as `ServiceRepositoryProtocol` from servicePhilosophy:

```python
@property
def factory(self) -> U: ...

@property
def maybe_factory(self) -> U | None: ...

@property
def has_factory(self) -> bool: ...
```

Optionally, document that `RepositoryFactory` / `AsyncRepositoryFactory` are sqlPhilosophy’s SQL-specific extensions of the empty `RepositoryFactoryProtocol` marker from servicePhilosophy. No SQL methods belong on the shared marker.

---

## Files expected to change (implementation phase)

| Area | Files |
|------|-------|
| Dependency | `pyproject.toml`, `uv.lock` |
| Sync repository | `src/sqlphilosophy/sync/repository.py` |
| Async repository | `src/sqlphilosophy/aio/repository.py` |
| Protocols | `src/sqlphilosophy/sync/protocols.py`, `src/sqlphilosophy/aio/protocols.py` |
| Tests | `tests/test_sync_repository.py`, `tests/test_async_repository.py`, `tests/test_repository_shared.py`, `tests/test_repository_parity.py`, factory/cross-repo tests |
| Docs | `docs/repository-guide.md`, `docs/feature-matrix.md`, `docs/usage/typed-repositories.md`, `docs/usage/strongly-typed-repositories.md`, `docs/examples/typed_repository_sync.py`, `docs/examples/typed_repository_async.py` |
| Changelog | `CHANGELOG.md` |

---

## Migration steps

1. **Add dependency on `servicephilosophy`.**  
   Add `servicephilosophy>=0.1.0` (or appropriate minimum) to `[project] dependencies` in `pyproject.toml`. Regenerate lockfile with `uv lock`.

2. **Import `ServiceRepository`.**  
   In sync and async repository modules:
   `from servicephilosophy import ServiceRepository`

3. **Make sync `BaseRepository` inherit from `ServiceRepository[U]`.**  
   Change the class declaration to inherit `ServiceRepository[U]` before or alongside existing bases. Remove duplicate `_factory` assignment if `super().__init__` owns it.

4. **Call `super().__init__(factory)` in sync repository constructor.**  
   Invoke before or after setting `model` / `_session` (order does not matter as long as both run). Do **not** assign `self._factory = factory` separately.

5. **Make async `AsyncBaseRepository` inherit from `ServiceRepository[U]`.**  
   Mirror the sync change in `src/sqlphilosophy/aio/repository.py`.

6. **Call `super().__init__(factory)` in async constructor.**  
   Same as sync step 4.

7. **Update protocols to expose `factory`, `maybe_factory`, and `has_factory`.**  
   Replace or supplement `_factory: U | None` on `BaseRepositoryProtocol` and `AsyncBaseRepositoryProtocol` with the property surface. Keep `_session` and SQL method signatures unchanged.

8. **Add tests for factory property behavior.**  
   Cover at minimum:
   - repository constructed with factory → `.factory` returns it
   - `.maybe_factory` / `.has_factory` when present and absent
   - `.factory` without factory → `FactoryRequiredError`
   - `statement()` still works with and without factory
   - `for_repo()` raises when factory missing (via `FactoryRequiredError` if using `self.factory`)

9. **Verify existing CRUD tests still pass.**  
   Run full suite: `uv run pytest`, `uv run mypy src`, `uv run ruff check src tests`. No CRUD, pagination, delete, or transaction tests should change outcome.

10. **Update docs and examples.**  
    - Document the layered relationship (servicePhilosophy base + sqlPhilosophy specialization).  
    - Replace `_factory` references in examples with `.factory` / `.has_factory` where appropriate.  
    - Update typed repository examples (`docs/examples/typed_repository_*.py`) to drop redundant `_app_factory()` helpers where `self.factory` suffices.  
    - Add a link to this plan from `docs/repository-guide.md` (optional).

---

## Testing checklist

- [ ] Sync: factory present — `.factory`, `.maybe_factory`, `.has_factory`
- [ ] Sync: factory absent — `.has_factory is False`, `.maybe_factory is None`, `.factory` raises
- [ ] Async: same factory property tests
- [ ] `statement()` without factory → direct `SqlAlchemyStatementBuilder` / `AsyncSqlAlchemyStatementBuilder`
- [ ] `statement()` with factory → `factory.create_statement(model)`
- [ ] `for_repo()` with factory → cached typed repo
- [ ] `for_repo()` without factory → error (document whether `FactoryRequiredError` or existing `RuntimeError` is kept)
- [ ] All existing CRUD / query / parity tests green
- [ ] Typed repository examples still runnable (`uv run python docs/examples/typed_repository_sync.py`, async variant)
- [ ] Import contract tests (`tests/test_import_contract.py`) updated if public exports change

---

## Non-goals (this integration)

- Changing CRUD method signatures or SQL semantics
- Moving model or session storage into servicePhilosophy
- Adding HTTP/API repository types (future **apiPhilosophy** concern)
- Requiring a factory for all repository construction (optional factory + `statement()` fallback stays)
- Implementing the code changes in this document

---

## Recommended ecosystem (after integration)

```text
servicePhilosophy
  ServiceRepository[FactoryT]

sqlPhilosophy
  BaseRepository[ModelT, FactoryT]
  AsyncBaseRepository[ModelT, FactoryT]

apiPhilosophy (future)
  BaseApiRepository[ResourceT, FactoryT]

application
  UserRepository(BaseRepository[User, AppFactory])
  PermissionServiceRepository(ServiceRepository[AppFactory])   # no model
```

Each layer adds one concern. sqlPhilosophy depends on servicePhilosophy for factory wiring only; applications depend on sqlPhilosophy for ORM repositories and may depend on servicePhilosophy directly for non-SQL services.
