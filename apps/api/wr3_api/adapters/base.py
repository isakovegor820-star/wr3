from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter

from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import Finding


@dataclass(frozen=True)
class NormalizedSource:
    chain: Chain
    address: str | None
    source: str
    contract_name: str = "Contract"
    file_name: str = "Contract.sol"


@dataclass(frozen=True)
class EngineRunOptions:
    audit_id: str
    timeout_seconds: int = 30


@dataclass
class EngineRunResult:
    engine: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    raw_output: str | None = None
    error: str | None = None
    duration_ms: int = 0


class EngineAdapter(ABC):
    name: str

    @abstractmethod
    async def version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def supports(self, source: NormalizedSource) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def run(self, source: NormalizedSource, options: EngineRunOptions) -> EngineRunResult:
        raise NotImplementedError


class Timer:
    def __enter__(self) -> "Timer":
        self.started = perf_counter()
        self.duration_ms = 0
        return self

    def __exit__(self, *_args: object) -> None:
        self.duration_ms = round((perf_counter() - self.started) * 1000)
