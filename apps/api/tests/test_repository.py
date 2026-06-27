from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import CreateAuditRequest, DisclosureCase
from wr3_api.services.repository import (
    InMemoryAuditRepository,
    InMemoryDisclosureRepository,
    SCHEMA_PATH,
    build_audit_repository,
)
from wr3_api.domain.schemas import AuditRecord


def test_in_memory_audit_repository_round_trips_record():
    repository = InMemoryAuditRepository()
    record = AuditRecord(
        request=CreateAuditRequest(
            chain=Chain.BASE,
            address="0x0000000000000000000000000000000000000000",
        )
    )
    repository.save(record)

    loaded = repository.get(record.audit_id)

    assert loaded is not None
    assert loaded.audit_id == record.audit_id
    assert repository.list_records()[0].audit_id == record.audit_id


def test_in_memory_disclosure_repository_round_trips_case():
    repository = InMemoryDisclosureRepository()
    case = DisclosureCase(finding_id="wr3-find-test")
    repository.save(case)

    assert repository.get(case.id) == case


def test_repository_factory_defaults_to_memory_without_database_url():
    assert isinstance(build_audit_repository(None), InMemoryAuditRepository)


def test_postgres_schema_file_contains_core_tables():
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    required_tables = [
        "users",
        "auth_accounts",
        "projects",
        "contracts",
        "audit_jobs",
        "audit_events",
        "engine_runs",
        "findings",
        "artifacts",
        "disclosure_cases",
        "benchmark_runs",
        "watchlist_entries",
    ]
    for table in required_tables:
        assert f"create table if not exists {table}" in schema
