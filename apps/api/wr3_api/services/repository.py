from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import AuditState
from wr3_api.domain.schemas import AuditRecord, DisclosureCase

try:  # Optional at import time so local memory-only tests do not need Postgres.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - exercised only in minimal installs
    psycopg = None
    Jsonb = None

try:
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - exercised only in minimal installs
    ConnectionPool = None


SCHEMA_PATH = Path(__file__).resolve().parents[4] / "infra" / "postgres" / "001_core_schema.sql"

_ENCRYPTION_MARKER = "wr3_enc_v1"
_POOLS: dict[str, Any] = {}


def _get_pool(database_url: str):
    """One pooled connection set per database URL, shared across repositories, so
    we stop paying a fresh TCP+auth handshake on every query."""
    pool = _POOLS.get(database_url)
    if pool is None:
        if ConnectionPool is None:  # pragma: no cover - minimal installs
            raise RuntimeError("psycopg_pool is required when WR3_DATABASE_URL is configured")
        pool = ConnectionPool(database_url, min_size=1, max_size=10, open=True)
        _POOLS[database_url] = pool
    return pool


def close_all_pools() -> None:
    """Close pooled connections on shutdown so the pool's worker thread is joined
    while the event loop is still alive (avoids a finalizer error at exit)."""
    for pool in list(_POOLS.values()):
        try:
            pool.close()
        except Exception:  # pragma: no cover - best-effort shutdown
            pass
    _POOLS.clear()


class _PayloadCipher:
    """Encrypts persisted record payloads at rest (the raw contract source lives
    here). Reuses the platform artifact key; without a key configured it stays
    plaintext for local dev and flags the gap to the caller."""

    def __init__(self, key: str | None, *, require: bool = False) -> None:
        # Fail closed: outside development a missing/typo'd key must not silently
        # fall back to writing contract source + findings in plaintext at rest.
        if require and not key:
            raise RuntimeError(
                "WR3_ARTIFACT_ENCRYPTION_KEY is required outside development — "
                "refusing to persist contract source/findings unencrypted."
            )
        self._key = key

    @property
    def active(self) -> bool:
        return bool(self._key)

    def encrypt(self, payload: dict) -> dict:
        if not self._key:
            return payload
        from cryptography.fernet import Fernet

        token = Fernet(self._key.encode("utf-8")).encrypt(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        return {_ENCRYPTION_MARKER: token.decode("utf-8")}

    def decrypt(self, stored: Any) -> Any:
        if not isinstance(stored, dict) or _ENCRYPTION_MARKER not in stored:
            return stored
        from cryptography.fernet import Fernet

        raw = Fernet(self._key.encode("utf-8")).decrypt(stored[_ENCRYPTION_MARKER].encode("utf-8"))
        return json.loads(raw)


class AuditRepository(Protocol):
    def save(self, record: AuditRecord) -> None: ...

    def get(self, audit_id: UUID) -> AuditRecord | None: ...

    def list_records(self) -> list[AuditRecord]: ...

    def list_queued_records(self, limit: int) -> list[AuditRecord]: ...

    def platform_counts(self) -> dict[str, int]: ...

    def delete(self, audit_id: UUID) -> bool: ...


class DisclosureRepository(Protocol):
    def save(self, case: DisclosureCase) -> None: ...

    def get(self, case_id: str) -> DisclosureCase | None: ...

    def list_cases(self) -> list[DisclosureCase]: ...


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, AuditRecord] = {}

    def save(self, record: AuditRecord) -> None:
        self._records[record.audit_id] = record

    def get(self, audit_id: UUID) -> AuditRecord | None:
        return self._records.get(audit_id)

    def list_records(self) -> list[AuditRecord]:
        return list(self._records.values())

    def list_queued_records(self, limit: int) -> list[AuditRecord]:
        queued = [r for r in self._records.values() if r.state == AuditState.QUEUED]
        queued.sort(key=lambda r: r.created_at)
        return queued[: max(limit, 0)]

    def platform_counts(self) -> dict[str, int]:
        records = list(self._records.values())
        return {
            "queued": sum(1 for r in records if r.state == AuditState.QUEUED),
            "completed": sum(1 for r in records if r.state == AuditState.COMPLETED),
            "confirmed": sum(1 for r in records for f in r.findings if str(f.exploitability) == "confirmed"),
        }

    def delete(self, audit_id: UUID) -> bool:
        return self._records.pop(audit_id, None) is not None


class InMemoryDisclosureRepository:
    def __init__(self) -> None:
        self._cases: dict[str, DisclosureCase] = {}

    def save(self, case: DisclosureCase) -> None:
        self._cases[case.id] = case

    def get(self, case_id: str) -> DisclosureCase | None:
        return self._cases.get(case_id)

    def list_cases(self) -> list[DisclosureCase]:
        return sorted(self._cases.values(), key=lambda case: case.created_at, reverse=True)


class PostgresAuditRepository:
    def __init__(self, database_url: str) -> None:
        if psycopg is None or Jsonb is None:
            raise RuntimeError("psycopg is required when WR3_DATABASE_URL is configured")
        self._database_url = database_url
        self._pool = _get_pool(database_url)
        self._cipher = _PayloadCipher(
            get_settings().artifact_encryption_key,
            require=get_settings().environment != "development",
        )
        self._ensure_schema()

    def save(self, record: AuditRecord) -> None:
        payload = self._cipher.encrypt(record.model_dump(mode="json"))
        with self._pool.connection() as conn:
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
        with self._pool.connection() as conn:
            row = conn.execute("select payload from audit_jobs where id = %s", (audit_id,)).fetchone()
        if row is None:
            return None
        return AuditRecord.model_validate(self._cipher.decrypt(row[0]))

    def list_records(self) -> list[AuditRecord]:
        with self._pool.connection() as conn:
            rows = conn.execute("select payload from audit_jobs order by updated_at asc").fetchall()
        return [AuditRecord.model_validate(self._cipher.decrypt(row[0])) for row in rows]

    def list_queued_records(self, limit: int) -> list[AuditRecord]:
        # Filter on the indexed state column so we only decrypt the few oldest
        # queued payloads, not the whole table, every drain cycle.
        with self._pool.connection() as conn:
            rows = conn.execute(
                "select payload from audit_jobs where state = %s order by created_at asc limit %s",
                (str(AuditState.QUEUED), max(limit, 0)),
            ).fetchall()
        return [AuditRecord.model_validate(self._cipher.decrypt(row[0])) for row in rows]

    def platform_counts(self) -> dict[str, int]:
        # Aggregate COUNTs on indexed columns — no payload decryption needed.
        with self._pool.connection() as conn:
            queued = conn.execute(
                "select count(*) from audit_jobs where state = %s", (str(AuditState.QUEUED),)
            ).fetchone()
            completed = conn.execute(
                "select count(*) from audit_jobs where state = %s", (str(AuditState.COMPLETED),)
            ).fetchone()
            # 'confirmed' == str(Exploitability.CONFIRMED): a forge-verified exploit.
            confirmed = conn.execute(
                "select count(*) from findings where exploitability = %s", ("confirmed",)
            ).fetchone()
        return {
            "queued": (queued or [0])[0],
            "completed": (completed or [0])[0],
            "confirmed": (confirmed or [0])[0],
        }

    def delete(self, audit_id: UUID) -> bool:
        with self._pool.connection() as conn:
            result = conn.execute("delete from audit_jobs where id = %s", (audit_id,))
            return (result.rowcount or 0) > 0

    def _ensure_schema(self) -> None:
        with self._pool.connection() as conn:
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
        self._pool = _get_pool(database_url)
        self._cipher = _PayloadCipher(
            get_settings().artifact_encryption_key,
            require=get_settings().environment != "development",
        )
        self._ensure_schema()

    def save(self, case: DisclosureCase) -> None:
        payload = self._cipher.encrypt(case.model_dump(mode="json"))
        with self._pool.connection() as conn:
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
        with self._pool.connection() as conn:
            row = conn.execute("select payload from disclosure_cases where id = %s", (case_id,)).fetchone()
        if row is None:
            return None
        return DisclosureCase.model_validate(self._cipher.decrypt(row[0]))

    def list_cases(self) -> list[DisclosureCase]:
        with self._pool.connection() as conn:
            rows = conn.execute("select payload from disclosure_cases order by updated_at desc").fetchall()
        return [DisclosureCase.model_validate(self._cipher.decrypt(row[0])) for row in rows]

    def _ensure_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def build_audit_repository(database_url: str | None) -> AuditRepository:
    if database_url:
        return PostgresAuditRepository(database_url)
    return InMemoryAuditRepository()


def build_disclosure_repository(database_url: str | None) -> DisclosureRepository:
    if database_url:
        return PostgresDisclosureRepository(database_url)
    return InMemoryDisclosureRepository()
