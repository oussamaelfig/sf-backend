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

- Every schema field carries a `description`, and user-facing fields carry
  `examples`. The OpenAPI guard tests in `tests/test_openapi.py` enforce
  this; a missing description is a broken build.
- Request-only validation must not run on response models: response
  serialization is a hot path and must not repeat expensive checks.
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
