from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from wr3_api.domain.schemas import AuditRecord, DisclosureCase

try:  # Optional at import time so local memory-only tests do not need Postgres.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - exercised only in minimal installs
    psycopg = None
    Jsonb = None


SCHEMA_PATH = Path(__file__).resolve().parents[4] / "infra" / "postgres" / "001_core_schema.sql"


class AuditRepository(Protocol):
    def save(self, record: AuditRecord) -> None: ...

    def get(self, audit_id: UUID) -> AuditRecord | None: ...

    def list_records(self) -> list[AuditRecord]: ...

    def delete(self, audit_id: UUID) -> bool: ...


class DisclosureRepository(Protocol):
    def save(self, case: DisclosureCase) -> None: ...

    def get(self, case_id: str) -> DisclosureCase | None: ...


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, AuditRecord] = {}

    def save(self, record: AuditRecord) -> None:
        self._records[record.audit_id] = record

    def get(self, audit_id: UUID) -> AuditRecord | None:
        return self._records.get(audit_id)

    def list_records(self) -> list[AuditRecord]:
        return list(self._records.values())

    def delete(self, audit_id: UUID) -> bool:
        return self._records.pop(audit_id, None) is not None


class InMemoryDisclosureRepository:
    def __init__(self) -> None:
        self._cases: dict[str, DisclosureCase] = {}

    def save(self, case: DisclosureCase) -> None:
        self._cases[case.id] = case

    def get(self, case_id: str) -> DisclosureCase | None:
        return self._cases.get(case_id)


class PostgresAuditRepository:
    def __init__(self, database_url: str) -> None:
        if psycopg is None or Jsonb is None:
            raise RuntimeError("psycopg is required when WR3_DATABASE_URL is configured")
        self._database_url = database_url
        self._ensure_schema()

    def save(self, record: AuditRecord) -> None:
        payload = record.model_dump(mode="json")
        with psycopg.connect(self._database_url) as conn:
            conn.execute(
                """
                insert into audit_jobs (
                    id, user_id, state, chain, address, source_hash, verified_at,
                    explorer_metadata, proxy_info, retention_until,
                    payload, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do update set
                    user_id = excluded.user_id,
                    state = excluded.state,
                    chain = excluded.chain,
                    address = excluded.address,
                    source_hash = excluded.source_hash,
                    verified_at = excluded.verified_at,
                    explorer_metadata = excluded.explorer_metadata,
                    proxy_info = excluded.proxy_info,
                    retention_until = excluded.retention_until,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    record.audit_id,
                    record.user_id,
                    str(record.state),
                    str(record.request.chain),
                    record.request.address,
                    record.source_metadata.source_hash,
                    record.source_metadata.verified_at,
                    Jsonb(record.source_metadata.explorer_metadata),
                    Jsonb(record.source_metadata.proxy_info.model_dump(mode="json")),
                    record.retention_until,
                    Jsonb(payload),
                    record.created_at,
                    record.updated_at,
                ),
            )
            self._replace_child_rows(conn, record)

    def get(self, audit_id: UUID) -> AuditRecord | None:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute("select payload from audit_jobs where id = %s", (audit_id,)).fetchone()
        if row is None:
            return None
        return AuditRecord.model_validate(row[0])

    def list_records(self) -> list[AuditRecord]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute("select payload from audit_jobs order by updated_at asc").fetchall()
        return [AuditRecord.model_validate(row[0]) for row in rows]

    def delete(self, audit_id: UUID) -> bool:
        with psycopg.connect(self._database_url) as conn:
            result = conn.execute("delete from audit_jobs where id = %s", (audit_id,))
            return (result.rowcount or 0) > 0

    def _ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    def _replace_child_rows(self, conn, record: AuditRecord) -> None:
        conn.execute("delete from audit_events where audit_id = %s", (record.audit_id,))
        conn.execute("delete from engine_runs where audit_id = %s", (record.audit_id,))
        conn.execute("delete from findings where audit_id = %s", (record.audit_id,))
        for event in record.events:
            conn.execute(
                """
                insert into audit_events (audit_id, event_type, payload, created_at)
                values (%s, %s, %s, %s)
                """,
                (
                    record.audit_id,
                    event.event_type,
                    Jsonb(event.payload),
                    event.created_at,
                ),
            )
        for run in record.engine_runs:
            conn.execute(
                """
                insert into engine_runs (id, audit_id, engine, status, duration_ms, artifact_uri, error, payload)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    record.audit_id,
                    run.engine,
                    run.status,
                    run.duration_ms,
                    run.artifact_uri,
                    run.error,
                    Jsonb(run.model_dump(mode="json")),
                ),
            )
        for finding in record.findings:
            conn.execute(
                """
                insert into findings (
                    id, audit_id, chain, severity, confidence, exploitability,
                    wr3_category, human_review_status, payload
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    finding.id,
                    record.audit_id,
                    str(finding.chain),
                    str(finding.severity),
                    finding.confidence,
                    str(finding.exploitability),
                    finding.taxonomy.wr3_category,
                    str(finding.human_review_status),
                    Jsonb(finding.model_dump(mode="json")),
                ),
            )


class PostgresDisclosureRepository:
    def __init__(self, database_url: str) -> None:
        if psycopg is None or Jsonb is None:
            raise RuntimeError("psycopg is required when WR3_DATABASE_URL is configured")
        self._database_url = database_url
        self._ensure_schema()

    def save(self, case: DisclosureCase) -> None:
        payload = case.model_dump(mode="json")
        with psycopg.connect(self._database_url) as conn:
            conn.execute(
                """
                insert into disclosure_cases (id, finding_id, status, payload, created_at, updated_at)
                values (%s, %s, %s, %s, %s, now())
                on conflict (id) do update set
                    finding_id = excluded.finding_id,
                    status = excluded.status,
                    payload = excluded.payload,
                    updated_at = now()
                """,
                (case.id, case.finding_id, case.status, Jsonb(payload), case.created_at),
            )

    def get(self, case_id: str) -> DisclosureCase | None:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute("select payload from disclosure_cases where id = %s", (case_id,)).fetchone()
        if row is None:
            return None
        return DisclosureCase.model_validate(row[0])

    def _ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def build_audit_repository(database_url: str | None) -> AuditRepository:
    if database_url:
        return PostgresAuditRepository(database_url)
    return InMemoryAuditRepository()


def build_disclosure_repository(database_url: str | None) -> DisclosureRepository:
    if database_url:
        return PostgresDisclosureRepository(database_url)
    return InMemoryDisclosureRepository()
