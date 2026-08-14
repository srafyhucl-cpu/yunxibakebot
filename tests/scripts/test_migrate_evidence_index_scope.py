from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import migrate_evidence_index_scope as mig


def _write_fixture(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "probe.py").write_text("probe", encoding="utf-8")
    index = tmp_path / "evidence-index.md"
    index.write_text(
        "# Evidence Index\n\n"
        "## E-20260814-200：迁移测试\n\n"
        "- trace_id: test\n"
        "- generated_at: 2026-08-14\n"
        "- evidence_type: governance/migrate-test\n"
        "- file: `scripts/probe.py`；`reports/harness/x.json`\n"
        "- command: x\n"
        "- result: pass\n"
        "- related_logbook: x\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: x\n"
        "- summary: x\n",
        encoding="utf-8",
    )
    return index


def _run(tmp_path: Path, monkeypatch, *, dry_run: bool = False) -> int:
    monkeypatch.setattr(mig, "ROOT_DIR", tmp_path)
    return mig.migrate(tmp_path / "evidence-index.md", dry_run=dry_run)


def test_migrates_prefix_scope_and_sha256(tmp_path: Path, monkeypatch) -> None:
    index = _write_fixture(tmp_path)
    assert _run(tmp_path, monkeypatch) == 0
    text = index.read_text(encoding="utf-8")
    assert "`repo:scripts/probe.py`" in text
    assert "`local:reports/harness/x.json`" in text
    assert "- storage_scope: repository" in text
    digest = hashlib.sha256(b"probe").hexdigest()
    assert f"- sha256: {digest}" in text


def test_migration_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    index = _write_fixture(tmp_path)
    _run(tmp_path, monkeypatch)
    first = index.read_text(encoding="utf-8")
    assert _run(tmp_path, monkeypatch) == 0
    assert index.read_text(encoding="utf-8") == first


def test_dry_run_does_not_write(tmp_path: Path, monkeypatch) -> None:
    index = _write_fixture(tmp_path)
    before = index.read_text(encoding="utf-8")
    assert _run(tmp_path, monkeypatch, dry_run=True) == 0
    assert index.read_text(encoding="utf-8") == before


def test_bom_heading_starts_new_entry(tmp_path: Path, monkeypatch) -> None:
    index = _write_fixture(tmp_path)
    text = index.read_text(encoding="utf-8")
    index.write_text(
        text + "\n\ufeff## E-20260814-201：BOM 条目\n\n"
        "- trace_id: bom\n"
        "- generated_at: 2026-08-14\n"
        "- evidence_type: governance/bom-test\n"
        "- file: `scripts/probe.py`\n"
        "- command: x\n"
        "- result: pass\n"
        "- related_logbook: x\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: x\n"
        "- summary: x\n",
        encoding="utf-8",
    )
    assert _run(tmp_path, monkeypatch) == 0
    migrated = index.read_text(encoding="utf-8")
    assert "## E-20260814-201：BOM 条目" in migrated
    assert "storage_scope: repository" in migrated
    assert "- storage_scope: repository" in migrated
