from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from wr3_api.core.config import get_settings

SENSITIVE_KINDS = {"source", "raw_output", "poc", "fuzzer_counterexample", "private_report", "finding"}


class ArtifactEncryptionRequired(PermissionError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    id: str
    kind: str
    uri: str
    private: bool
    encrypted: bool
    sha256: str


class ArtifactVault:
    def __init__(
        self,
        *,
        root_dir: str | Path | None = None,
        encryption_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self._root = Path(root_dir or settings.artifact_dir)
        self._encryption_key = encryption_key if encryption_key is not None else settings.artifact_encryption_key

    def store_json(
        self,
        *,
        audit_id: str,
        kind: str,
        payload: dict[str, object],
        private: bool = True,
    ) -> StoredArtifact:
        sensitive = private or kind in SENSITIVE_KINDS
        if sensitive and not self._encryption_key:
            raise ArtifactEncryptionRequired("artifact_encryption_key_required_for_sensitive_artifact")
        artifact_id = f"wr3-artifact-{uuid4()}"
        artifact_dir = self._root / audit_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encrypted = False
        if sensitive:
            data = self._encrypt(data)
            encrypted = True
        path = artifact_dir / f"{artifact_id}.json{' .enc' if encrypted else ''}".replace(" ", "")
        path.write_bytes(data)
        return StoredArtifact(
            id=artifact_id,
            kind=kind,
            uri=f"local-artifact://{audit_id}/{path.name}",
            private=private,
            encrypted=encrypted,
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def _encrypt(self, data: bytes) -> bytes:
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ArtifactEncryptionRequired("cryptography_extra_required_for_sensitive_artifact") from exc
        return Fernet(self._encryption_key.encode("utf-8")).encrypt(data)
