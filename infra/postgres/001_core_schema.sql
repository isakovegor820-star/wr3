create table if not exists users (
    id text primary key,
    email text,
    risk_flags jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists auth_accounts (
    id text primary key,
    user_id text not null references users(id) on delete cascade,
    provider text not null,
    provider_subject text not null,
    created_at timestamptz not null default now(),
    unique(provider, provider_subject)
);

create table if not exists projects (
    id uuid primary key,
    owner_user_id text not null references users(id) on delete cascade,
    name text not null,
    visibility text not null default 'private',
    created_at timestamptz not null default now()
);

create table if not exists contracts (
    id uuid primary key,
    chain text not null,
    address text,
    source_hash text,
    verified_at timestamptz,
    proxy_info jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique(chain, address, source_hash)
);

create table if not exists audit_jobs (
    id uuid primary key,
    user_id text,
    contract_id uuid references contracts(id) on delete set null,
    state text not null,
    chain text not null,
    address text,
    source_hash text,
    verified_at timestamptz,
    explorer_metadata jsonb not null default '{}'::jsonb,
    proxy_info jsonb not null default '{}'::jsonb,
    retention_until timestamptz,
    payload jsonb not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists idx_audit_jobs_chain_address on audit_jobs (chain, address);
create index if not exists idx_audit_jobs_state on audit_jobs (state);
create index if not exists idx_audit_jobs_updated_at on audit_jobs (updated_at desc);
create index if not exists idx_audit_jobs_retention_until on audit_jobs (retention_until);

create table if not exists audit_events (
    id bigserial primary key,
    audit_id uuid not null references audit_jobs(id) on delete cascade,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists engine_runs (
    id uuid primary key,
    audit_id uuid not null references audit_jobs(id) on delete cascade,
    engine text not null,
    status text not null,
    duration_ms integer not null default 0,
    artifact_uri text,
    error text,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists findings (
    id text primary key,
    audit_id uuid not null references audit_jobs(id) on delete cascade,
    chain text not null,
    severity text not null,
    confidence numeric not null,
    exploitability text not null,
    wr3_category text not null,
    human_review_status text not null,
    payload jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists artifacts (
    id text primary key,
    audit_id uuid references audit_jobs(id) on delete cascade,
    uri text not null,
    kind text not null,
    private boolean not null default true,
    encryption_key_ref text,
    retention_until timestamptz,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists disclosure_cases (
    id text primary key,
    finding_id text not null,
    status text not null,
    payload jsonb not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists idx_disclosure_cases_finding_id on disclosure_cases (finding_id);
create index if not exists idx_disclosure_cases_status on disclosure_cases (status);

create table if not exists benchmark_runs (
    id uuid primary key,
    dataset text not null,
    commit_sha text,
    metrics jsonb not null,
    artifact_uri text,
    created_at timestamptz not null default now()
);

create table if not exists watchlist_entries (
    id text primary key,
    user_id text not null references users(id) on delete cascade,
    chain text not null,
    address text not null,
    label text,
    alert_channels jsonb not null default '[]'::jsonb,
    status text not null default 'active',
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_contracts_chain_address on contracts(chain, address);
create index if not exists idx_audit_events_audit_id on audit_events(audit_id);
create index if not exists idx_engine_runs_audit_id on engine_runs(audit_id);
create index if not exists idx_findings_audit_id on findings(audit_id);
create index if not exists idx_findings_severity on findings(severity);
create index if not exists idx_artifacts_audit_id_kind on artifacts(audit_id, kind);
create index if not exists idx_benchmark_runs_dataset on benchmark_runs(dataset);
create index if not exists idx_watchlist_user_chain_address on watchlist_entries(user_id, chain, address);
