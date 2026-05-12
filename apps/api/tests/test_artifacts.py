import pytest

from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault


def test_sensitive_artifact_requires_encryption_key(tmp_path):
    vault = ArtifactVault(root_dir=tmp_path, encryption_key="")

    with pytest.raises(ArtifactEncryptionRequired):
        vault.store_json(
            audit_id="audit-1",
            kind="poc",
            payload={"trace": "private"},
            private=True,
        )


def test_public_manifest_can_be_written_without_encryption(tmp_path):
    vault = ArtifactVault(root_dir=tmp_path, encryption_key="")

    artifact = vault.store_json(
        audit_id="audit-1",
        kind="manifest",
        payload={"status": "ok"},
        private=False,
    )

    assert artifact.encrypted is False
    assert artifact.private is False
    assert artifact.uri.startswith("local-artifact://audit-1/")


def test_sensitive_artifact_reports_missing_crypto_extra_or_encrypts(tmp_path):
    vault = ArtifactVault(
        root_dir=tmp_path,
        encryption_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )

    try:
        artifact = vault.store_json(
            audit_id="audit-1",
            kind="raw_output",
            payload={"raw": "private"},
            private=True,
        )
    except ArtifactEncryptionRequired as exc:
        assert "cryptography_extra_required" in str(exc)
    else:
        assert artifact.encrypted is True
