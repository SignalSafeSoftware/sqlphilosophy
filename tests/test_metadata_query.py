"""Metadata composition never acquires a session and cannot execute a query."""

from collections.abc import Callable
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from conftest import Widget
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder


def test_metadata_composition_requires_no_session() -> None:
    with patch.object(Session, "__init__", side_effect=AssertionError("Unexpected Session")):
        query = (
            SqlAlchemyStatementBuilder.for_metadata(Widget)
            .select_columns(Widget.id, Widget.name)
            .where(Widget.active.is_(True))
            .order_by(Widget.id)
            .limit(3)
        )
        expected = select(Widget.id, Widget.name).where(Widget.active.is_(True)).order_by(Widget.id).limit(3)
        assert str(query.build_select()) == str(expected)
        assert set(query.build_select().subquery("metadata_rows").c.keys()) == {"id", "name"}


@pytest.mark.parametrize(
    "terminal",
    [
        lambda query: query.count(),
        lambda query: query.count_distinct(Widget.id),
        lambda query: query.scalar(),
        lambda query: query.scalar_one(),
        lambda query: query.mappings(),
        lambda query: query.scalars(),
        lambda query: query.fetch_page(ListQuery(limit=2, offset=0)),
    ],
)
def test_metadata_builder_rejects_every_execution_terminal(
    terminal: Callable[[SqlAlchemyStatementBuilder[Widget]], object],
) -> None:
    query = SqlAlchemyStatementBuilder.for_metadata(Widget).where(Widget.active.is_(True))
    with pytest.raises(RuntimeError, match="Metadata-only statement builders cannot execute"):
        terminal(query)
