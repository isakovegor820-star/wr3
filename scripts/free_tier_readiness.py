from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    area: str
    status: str
    evidence: str
    next_step: str


def env_present(name: str) -> bool:
    return bool(os.getenv(name))


def tool_present(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    checks = [
        ReadinessCheck(
            "cloudflare",
            "edge/artifacts",
            "configured" if env_present("CLOUDFLARE_ACCOUNT_ID") else "todo",
            "CLOUDFLARE_ACCOUNT_ID present" if env_present("CLOUDFLARE_ACCOUNT_ID") else "Cloudflare account not detected",
            "Create Cloudflare Free account, R2 buckets, D1 db, and API token.",
        ),
        ReadinessCheck(
            "oracle_vm",
            "compute",
            "manual",
            "Cannot verify remote Oracle VM from local env.",
            "Provision Always Free VM and record SSH host outside repo.",
        ),
        ReadinessCheck(
            "secrets",
            "secrets",
            "configured" if env_present("DOPPLER_TOKEN") or env_present("OCI_CLI_PROFILE") else "todo",
            "Doppler or OCI profile detected" if env_present("DOPPLER_TOKEN") or env_present("OCI_CLI_PROFILE") else "No secret manager token/profile detected",
            "Use Doppler Developer Free or OCI Vault; never commit .env.",
        ),
        ReadinessCheck(
            "sentry",
            "observability",
            "configured" if env_present("WR3_SENTRY_DSN") else "todo",
            "WR3_SENTRY_DSN present" if env_present("WR3_SENTRY_DSN") else "Sentry DSN not configured",
            "Create Sentry Developer project and enable scrubber before-send hook.",
        ),
        ReadinessCheck(
            "telegram",
            "distribution",
            "configured" if env_present("WR3_TELEGRAM_BOT_TOKEN") else "todo",
            "WR3_TELEGRAM_BOT_TOKEN present" if env_present("WR3_TELEGRAM_BOT_TOKEN") else "Telegram bot token not configured",
            "Create bot with BotFather and set webhook secret.",
        ),
        ReadinessCheck(
            "etherscan",
            "explorer",
            "configured" if env_present("WR3_ETHERSCAN_API_KEY") else "todo",
            "WR3_ETHERSCAN_API_KEY present" if env_present("WR3_ETHERSCAN_API_KEY") else "Etherscan V2 key not configured",
            "Create free Etherscan V2 key and keep app below 3 calls/sec.",
        ),
        ReadinessCheck(
            "alchemy",
            "rpc",
            "configured" if any(env_present(name) for name in ["ETHEREUM_FORK_RPC_URL", "BASE_FORK_RPC_URL", "ALCHEMY_API_KEY"]) else "todo",
            "RPC env present" if any(env_present(name) for name in ["ETHEREUM_FORK_RPC_URL", "BASE_FORK_RPC_URL", "ALCHEMY_API_KEY"]) else "No Alchemy/free RPC env detected",
            "Create Alchemy free app and add per-chain fork RPC URLs.",
        ),
        ReadinessCheck(
            "openrouter_zdr",
            "llm",
            "configured" if env_present("WR3_OPENROUTER_API_KEY") or env_present("OPENROUTER_API_KEY") else "optional",
            "OpenRouter key present" if env_present("WR3_OPENROUTER_API_KEY") or env_present("OPENROUTER_API_KEY") else "ZDR paid path disabled; deterministic fallback active",
            "Use only for paid/security-sensitive scans with provider.zdr=true.",
        ),
        ReadinessCheck(
            "sandbox_tools",
            "sandbox",
            "partial" if any(tool_present(tool) for tool in ["forge", "medusa", "ityfuzz", "trident"]) else "todo",
            ", ".join(tool for tool in ["forge", "anvil", "medusa", "ityfuzz", "trident"] if tool_present(tool)) or "No sandbox audit tools found in PATH",
            "Build sandbox image with Foundry, Medusa, ItyFuzz, Trident and no DB credentials.",
        ),
        ReadinessCheck(
            "payments",
            "billing",
            "partial" if env_present("WR3_USDC_RECEIVE_ADDRESS") else "todo",
            "USDC receive address configured" if env_present("WR3_USDC_RECEIVE_ADDRESS") else "No manual USDC address configured",
            "Start with manual USDC; add Request/Polar/Lemon only when beta customer needs it.",
        ),
    ]

    summary = {
        "configured": sum(check.status == "configured" for check in checks),
        "partial": sum(check.status == "partial" for check in checks),
        "todo": sum(check.status == "todo" for check in checks),
        "optional": sum(check.status == "optional" for check in checks),
        "manual": sum(check.status == "manual" for check in checks),
    }
    print(json.dumps({"summary": summary, "checks": [asdict(check) for check in checks]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
