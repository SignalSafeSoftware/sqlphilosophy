# sqlPhilosophy source and release preparation

Source baseline: verified main `57b82f96ee887f0c42faeb5dfa8c970995981060`.
This checkout prepares 0.3.4; public 0.3.3 remains the published baseline until a
separately approved release. This document certifies no host deployment.

Sync/async repositories own SQL statement composition, projection, ordering,
counts and persistence helpers. Applications supply model-specific repository
methods, session/factory lifecycle, authorization and transaction boundaries.
`apply_scope` affects the expression lookup helpers; it does not retroactively
scope all CRUD/query operations. See [the repository guide](repository-guide.md)
and [typed examples](examples/).

Strict decoders retain exact input checks, stable failures and object identity.
They never coerce booleans to numbers or list subclasses/custom class attributes
into plain lists. Raw SQL identifiers/fragments remain developer-owned; external
values must be bound. Normal CRUD does not commit; `batched_purge_ids` is the
explicit committing exception described in the [delete guide](usage/deletes.md).

SQLAlchemy stays `>=2.0,<3`; the candidate dependency baseline is
`servicephilosophy>=0.1.2,<0.2`. Build/test dependency locks are separate from
runtime support. Candidate wheels are tested with exact upstream candidate
archives; after upstream approval/publication, regenerate the real registry lock
and rerun frozen CI before publishing this dependent package. No temporary local
source overrides or fabricated registry URLs belong in the release source.
