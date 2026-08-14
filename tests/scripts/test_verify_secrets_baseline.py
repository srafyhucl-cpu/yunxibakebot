from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from scripts import verify_secrets_baseline as vsb


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / ".secrets.baseline").write_text("{}", encoding="utf-8")
    _git(repo, "add", ".secrets.baseline")
    _git(repo, "commit", "-m", "init")
    return repo


def _run(tmp_path: Path, monkeypatch) -> int:
    monkeypatch.setattr(vsb, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        vsb,
        "CHANGES_LOG",
        tmp_path
        / "docs"
        / "harness-engineering"
        / "core"
        / "secrets-baseline-changes.md",
    )
    return vsb.main()


def test_clean_worktree_passes(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    assert _run(repo, monkeypatch) == 0


def test_worktree_pollution_fails(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    (repo / ".secrets.baseline").write_text("{}polluted", encoding="utf-8")
    assert _run(repo, monkeypatch) == 1


def test_staged_change_without_record_fails(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    (repo / ".secrets.baseline").write_text("{staged}", encoding="utf-8")
    _git(repo, "add", ".secrets.baseline")
    assert _run(repo, monkeypatch) == 1


def test_staged_change_with_approved_record_passes(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    old_sha = hashlib.sha256(b"{}").hexdigest()
    (repo / ".secrets.baseline").write_text("{staged}", encoding="utf-8")
    _git(repo, "add", ".secrets.baseline")
    new_sha = hashlib.sha256(b"{staged}").hexdigest()
    log = repo / "docs" / "harness-engineering" / "core" / "secrets-baseline-changes.md"
    log.parent.mkdir(parents=True)
    log.write_text(
        f"## [2026-08-14] - secrets baseline 受控更新\n"
        f"- old_sha256: {old_sha}\n"
        f"- new_sha256: {new_sha}\n"
        f"- command: detect-secrets scan --all-files\n"
        f"- version: detect-secrets 1.5.0\n"
        f"- trace_id: test\n"
        f"- approved_by: project owner\n",
        encoding="utf-8",
    )
    assert _run(repo, monkeypatch) == 0


def test_missing_record_file_with_clean_worktree_passes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _init_repo(tmp_path)
    assert _run(repo, monkeypatch) == 0
