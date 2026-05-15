FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WR3_SANDBOX_MODE=1 \
    WR3_DATABASE_URL= \
    WR3_TASK_BACKEND=local

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    iproute2 \
    nodejs \
    npm \
  && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash wr3sandbox

WORKDIR /opt/wr3
COPY apps/api ./apps/api
COPY scripts ./scripts
COPY infra/sandbox/entrypoint.sh /usr/local/bin/wr3-sandbox-entrypoint

RUN python -m venv /opt/wr3/.venv \
  && /opt/wr3/.venv/bin/python -m pip install --upgrade pip \
  && /opt/wr3/.venv/bin/python -m pip install -e "apps/api[secure]"

USER wr3sandbox
WORKDIR /work

ENTRYPOINT ["/usr/local/bin/wr3-sandbox-entrypoint"]
