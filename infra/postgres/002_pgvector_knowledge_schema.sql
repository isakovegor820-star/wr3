-- Optional production migration for wr3 RAG.
-- Run only on Postgres instances with pgvector installed.

create extension if not exists vector;

create table if not exists knowledge_documents (
    id text primary key,
    source text not null,
    title text not null,
    content_hash text not null unique,
    tags text[] not null default '{}',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists knowledge_chunks (
    id text primary key,
    document_id text not null references knowledge_documents(id) on delete cascade,
    chunk_index integer not null,
    text text not null,
    token_count integer not null,
    embedding vector(768),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique(document_id, chunk_index)
);

create index if not exists idx_knowledge_documents_source on knowledge_documents(source);
create index if not exists idx_knowledge_documents_tags on knowledge_documents using gin(tags);
create index if not exists idx_knowledge_chunks_document_id on knowledge_chunks(document_id);
create index if not exists idx_knowledge_chunks_embedding
    on knowledge_chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
