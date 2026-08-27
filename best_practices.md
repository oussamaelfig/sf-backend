# Review standards for sf-backend

Qodo Merge applies these project-specific standards when reviewing pull
requests on this repository.

## Architecture

- Respect the layering: `models.py` (ORM) → `schemas.py` (validation) →
  `crud.py` (data access) → `routers/` (HTTP). Logic must live in the
  lowest layer that can own it; routers stay thin.
- Validation happens once, at the API boundary (Pydantic schemas). CRUD
  functions trust already-validated payloads and must not re-validate.

## SQLAlchemy

- Use SQLAlchemy 2.0 typed style only: `Mapped[...]` annotations with
  `mapped_column(...)`. Legacy `Column = Column(...)` declarations are a
  review failure.
- Relationships that own their children declare
  `cascade="all, delete-orphan"` and a matching `ondelete` on the FK.
- One-to-many data belongs in its own table with a foreign key — never
  numbered columns (`address2`, `address3`) and never JSON blobs.

## Pydantic / OpenAPI

- Every schema field carries a `description`. The OpenAPI guard tests in
  `tests/test_openapi.py` enforce this on `ContactRead` (a missing
  description is a broken build); other schemas must follow the same
  convention. Request schemas carry model-level examples, and key
  user-facing fields (like `email`) carry field-level examples.
- Request-only validation (format checks, decode-and-measure work) must
  not be reused on response models: reads are a hot path. Response-specific
  normalization (e.g. `ContactRead` restoring UTC tzinfo that SQLite
  drops) is intentional and fine.
- `ContactCreate.required` stays exactly `{first_name, last_name, email}`.

## Tests

- Every behavior change ships with tests in the same PR.
- The suite must stay fast (currently well under one second); no sleeps,
  no network, no fixtures heavier than the in-memory database.

## Diff hygiene

- Minimal diffs: no drive-by refactors, no dead code, no commented-out
  code, no unrelated formatting churn.
- New endpoints require documented `operationId`, `summary`, response
  models, and error responses — and a matching update to the OpenAPI
  guard tests.
